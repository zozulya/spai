"""
Quality Gate Component

Evaluates article quality using LLM judge.
Regenerates articles that fail, with feedback for improvement.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class QualityResult:
    """Result from quality check"""
    passed: bool
    score: float
    issues: List[str]
    cost: float


class QualityGate:
    """Quality checking with smart regeneration"""
    
    def __init__(self, llm_client, config: Dict, logger: logging.Logger):
        self.llm = llm_client
        self.config = config
        self.logger = logger.getChild('QualityGate')
        
        self.quality_config = config['quality_gate']
        self.min_score = self.quality_config['min_score']
        self.max_attempts = self.quality_config['max_attempts']
        self.llm_config = config['llm']
    
    def check_and_improve(
        self,
        article: Dict,
        sources: List[Dict],
        generator
    ) -> Tuple[Optional[Dict], QualityResult]:
        """
        Check quality and regenerate if needed
        
        Args:
            article: Article to check
            sources: Original sources (for regeneration)
            generator: ContentGenerator instance (for regeneration)
        
        Returns:
            (final_article or None, quality_result)
        """
        attempts = []
        current_article = article
        
        for attempt in range(1, self.max_attempts + 1):
            self.logger.debug(f"Quality check attempt {attempt}")
            
            # Evaluate current version
            result = self._evaluate(current_article)
            
            attempts.append({
                'attempt': attempt,
                'score': result.score,
                'issues': result.issues
            })
            
            if result.passed:
                self.logger.info(f"✅ Passed on attempt {attempt} (score: {result.score:.1f})")
                return current_article, result
            
            # Failed - should we try again?
            if attempt >= self.max_attempts:
                self.logger.warning(f"❌ Failed after {attempt} attempts (final: {result.score:.1f})")
                return None, result
            
            # Regenerate with feedback
            self.logger.info(f"🔄 Regenerating (attempt {attempt+1}) - score was {result.score:.1f}")
            self.logger.debug(f"   Issues: {', '.join(result.issues[:3])}")
            
            current_article = generator.regenerate_with_feedback(
                topic=current_article['topic'],
                sources=sources,
                level=current_article['level'],
                previous_attempt=current_article,
                issues=result.issues
            )
        
        return None, result
    
    def _evaluate(self, article: Dict) -> QualityResult:
        """Evaluate article quality using LLM judge"""
        
        prompt = self._build_judge_prompt(article)
        
        response = self._call_llm(prompt)
        
        result = self._parse_judge_response(response)
        
        score = result.get('total_score', 0)
        issues = result.get('issues', ['Could not evaluate'])
        
        return QualityResult(
            passed=(score >= self.min_score),
            score=score,
            issues=issues,
            cost=0.008  # Rough estimate
        )
    
    def _build_judge_prompt(self, article: Dict) -> str:
        """Build prompt for LLM judge"""
        
        level = article['level']
        
        level_criteria = {
            'A2': """
A2 Level Grammar Expectations:
- Present tense (presente) should be primary
- Simple past (pretérito) for completed actions only
- NO subjunctive mood
- Simple sentence structures
- Basic connectors (y, pero, porque, cuando)
""",
            'B1': """
B1 Level Grammar Expectations:
- Mixed tenses: presente, pretérito, imperfecto
- Subjunctive in common expressions (espero que, es importante que)
- More complex sentences with subordinate clauses
- Varied connectors (aunque, mientras, sin embargo, ya que)
"""
        }
        
        return f"""You are a Spanish language teaching expert. Evaluate this article for {level} level learners.

ARTICLE:
Title: {article['title']}
Level: {level}
Content:
{article['content']}

Vocabulary provided: {len(article.get('vocabulary', {}))} words

EVALUATION CRITERIA (total 0-10 points):

1. Grammar & Language (0-4 points):
{level_criteria[level]}
- Are there any grammar errors?
- Is the grammar appropriate for {level}?

2. Educational Value (0-3 points):
- Is this interesting and useful for Spanish learners?
- Does it teach cultural concepts?
- Are the vocabulary words relevant and useful?

3. Content Quality (0-2 points):
- Is the information accurate and coherent?
- Is it well-structured (clear paragraphs)?
- Does it flow naturally?

4. Level Appropriateness (0-1 point):
- Is vocabulary suitable for {level}?
- Is sentence complexity appropriate?
- Would this engage {level} learners?

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "grammar_score": 0-4,
  "grammar_issues": ["specific issue 1", "specific issue 2"] or [],
  
  "educational_score": 0-3,
  "educational_notes": "brief comment",
  
  "content_score": 0-2,
  "content_issues": ["issue1"] or [],
  
  "level_score": 0-1,
  
  "total_score": sum_of_all_scores,
  
  "issues": ["All specific issues that need fixing"],
  "strengths": ["What the article does well"],
  
  "verdict": "PASS" or "FAIL"
}}

Be strict but fair. A score of 7.5+ should mean genuinely good educational content.
7.5 is the minimum passing score.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM judge model"""
        model = self.llm_config['models']['quality_check']
        
        # Detect provider
        if hasattr(self.llm, 'messages'):  # Anthropic
            response = self.llm.messages.create(
                model=model,
                max_tokens=2048,
                temperature=0.1,  # Low temp for consistent judging
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        else:  # OpenAI
            response = self.llm.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048
            )
            return response.choices[0].message.content
    
    def _parse_judge_response(self, response: str) -> Dict:
        """Parse LLM judge response"""
        
        # Extract JSON
        json_str = response
        
        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]
        
        try:
            result = json.loads(json_str.strip())
            return result
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse judge response: {e}")
            self.logger.debug(f"Response was: {response[:500]}")
            
            # Return failure
            return {
                'total_score': 0.0,
                'verdict': 'FAIL',
                'issues': ['Could not parse evaluation response']
            }

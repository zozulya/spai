"""
Content Generator Component

Generates original Spanish articles by synthesizing multiple sources using LLM.
Supports regeneration with feedback for quality improvement.
"""

import json
import logging
from typing import Dict, List, Optional


class ContentGenerator:
    """Generates articles from multiple sources using LLM"""
    
    def __init__(self, llm_client, config: Dict, logger: logging.Logger):
        self.llm = llm_client
        self.config = config
        self.logger = logger.getChild('ContentGenerator')
        
        self.generation_config = config['generation']
        self.llm_config = config['llm']
    
    def generate_article(
        self,
        topic: Dict,
        sources: List[Dict],
        level: str
    ) -> Dict:
        """
        Generate initial article (no feedback)
        
        Args:
            topic: Topic dict from discovery
            sources: List of source content dicts
            level: 'A2' or 'B1'
        
        Returns:
            Article dict with title, content, vocabulary, etc.
        """
        prompt = self._build_prompt(topic, sources, level, feedback=None)
        
        response = self._call_llm(prompt)
        
        article = self._parse_response(response, topic, level, sources)
        
        self.logger.debug(f"Generated {level} article: {article['title']}")
        
        return article
    
    def regenerate_with_feedback(
        self,
        topic: Dict,
        sources: List[Dict],
        level: str,
        previous_attempt: Dict,
        issues: List[str]
    ) -> Dict:
        """
        Regenerate article with feedback about issues
        
        Args:
            topic: Topic dict
            sources: Source content
            level: CEFR level
            previous_attempt: Previous article that failed
            issues: List of specific issues to fix
        
        Returns:
            New improved article
        """
        feedback = {
            'previous_title': previous_attempt['title'],
            'previous_content': previous_attempt['content'],
            'issues': issues
        }
        
        prompt = self._build_prompt(topic, sources, level, feedback=feedback)
        
        response = self._call_llm(prompt, temperature=0.4)  # Slightly higher temp
        
        article = self._parse_response(response, topic, level, sources)
        
        self.logger.debug(f"Regenerated {level} article with feedback")
        
        return article
    
    def _build_prompt(
        self,
        topic: Dict,
        sources: List[Dict],
        level: str,
        feedback: Optional[Dict] = None
    ) -> str:
        """Build generation prompt"""
        
        word_count = self.generation_config['target_word_count'][level]
        
        # Level-specific instructions
        level_rules = {
            'A2': """
- Use ONLY present tense (presente)
- Simple sentences (max 12 words per sentence)
- Vocabulary: Only the 1000 most common Spanish words
- NO subjunctive mood
- Short, clear sentences
""",
            'B1': """
- Mix tenses: present, preterite (pretérito), imperfect (imperfecto)
- Varied sentence length (8-18 words)
- Intermediate vocabulary
- You may use subjunctive in common expressions only
- Some complex sentences with subordinate clauses
"""
        }
        
        # Prepare source context
        source_context = self._prepare_source_context(sources)
        
        # Base prompt
        base_prompt = f"""You are a Spanish language teacher creating educational content for {level} level students.

TOPIC: {topic['title']}

REFERENCE SOURCES (synthesize information, DO NOT copy text):
{source_context}

TASK: Create an ORIGINAL article in Spanish that:
1. Synthesizes information from the sources above in your own words
2. Is appropriate for {level} Spanish learners
3. Is approximately {word_count} words long
4. Has 3 clear paragraphs with good flow
5. Includes cultural context relevant to Spanish speakers
6. Is engaging and educational

LEVEL REQUIREMENTS for {level}:
{level_rules[level]}

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "title": "Engaging title in Spanish (5-8 words)",
  "content": "Full article text in Spanish (~{word_count} words, 3 paragraphs)",
  "vocabulary": {{
    "word1": "English translation",
    "word2": "English translation"
  }},
  "summary": "One sentence summary in Spanish",
  "reading_time": estimated_minutes_as_integer
}}

CRITICAL RULES:
- Write ORIGINAL content - synthesize ideas but use your own words
- DO NOT copy phrases from the sources
- This is educational fair use - transform the information

Attribution line to add at end of content:
"Fuentes: {', '.join([s['source'] for s in sources[:3]])}"
"""
        
        # Add feedback section if this is a regeneration
        if feedback:
            first_200 = ' '.join(feedback['previous_content'].split()[:200])
            
            feedback_section = f"""

⚠️ IMPORTANT: PREVIOUS ATTEMPT HAD ISSUES - YOU MUST FIX THEM

Previous Title: {feedback['previous_title']}

Previous Content (first 200 words):
{first_200}...

SPECIFIC ISSUES TO FIX:
{chr(10).join(f"- {issue}" for issue in feedback['issues'])}

Generate a NEW, IMPROVED version that specifically addresses these issues.
Make sure to fix the problems mentioned above.
"""
            return base_prompt + feedback_section
        
        return base_prompt
    
    def _prepare_source_context(self, sources: List[Dict]) -> str:
        """Prepare source text for prompt (truncated)"""
        context = []
        
        for i, source in enumerate(sources[:5], 1):
            context.append(f"""Source {i} ({source['source']}):
{source['text']}
""")
        
        return '\n\n'.join(context)
    
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM with prompt"""
        model = self.llm_config['models']['generation']
        
        # Detect provider type
        if hasattr(self.llm, 'messages'):  # Anthropic
            response = self.llm.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        else:  # OpenAI
            response = self.llm.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096
            )
            return response.choices[0].message.content
    
    def _parse_response(
        self,
        response: str,
        topic: Dict,
        level: str,
        sources: List[Dict]
    ) -> Dict:
        """Parse LLM JSON response into article dict"""
        
        # Extract JSON from response (handle markdown code blocks)
        json_str = response
        
        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]
        
        try:
            parsed = json.loads(json_str.strip())
            
            # Add metadata
            parsed['topic'] = topic
            parsed['level'] = level
            parsed['sources'] = [s['source'] for s in sources]
            
            # Ensure vocabulary is present
            if 'vocabulary' not in parsed or not parsed['vocabulary']:
                parsed['vocabulary'] = {}
            
            return parsed
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            self.logger.debug(f"Response was: {response[:500]}")
            
            # Return fallback article
            return {
                'title': f"{topic['title']} ({level})",
                'content': "Error: Could not parse LLM response",
                'vocabulary': {},
                'summary': '',
                'reading_time': 3,
                'topic': topic,
                'level': level,
                'sources': [s['source'] for s in sources]
            }

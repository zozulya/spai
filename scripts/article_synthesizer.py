"""
Article Synthesizer - Step 1 of Two-Step Generation

Synthesizes multiple source articles into one coherent native-level
Spanish article. No level adjustment - focuses on factual accuracy
and natural Spanish expression.
"""

import json
import logging
from typing import Dict, List


class ArticleSynthesizer:
    """Synthesizes native-level Spanish articles from multiple sources"""

    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('ArticleSynthesizer')
        self.llm_config = config['llm']

        # Initialize LLM client
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize LLM client (Anthropic or OpenAI) based on config"""
        provider = self.llm_config['provider']

        if provider == 'anthropic':
            api_key = self.llm_config.get('anthropic_api_key')
            if not api_key:
                raise ValueError("Missing ANTHROPIC_API_KEY in config/environment")

            from anthropic import Anthropic
            self.llm_client = Anthropic(api_key=api_key)
            self.logger.info("Initialized Anthropic client for synthesis")

        elif provider == 'openai':
            api_key = self.llm_config.get('openai_api_key')
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY in config/environment")

            from openai import OpenAI
            self.llm_client = OpenAI(api_key=api_key)
            self.logger.info("Initialized OpenAI client for synthesis")

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def synthesize(self, topic: Dict, sources: List[Dict]) -> Dict:
        """
        Synthesize native-level article from multiple sources

        Args:
            topic: Topic dict from discovery with 'title' key
            sources: List of source content dicts with 'source' and 'text' keys

        Returns:
            Base article dict with:
            - title (Spanish)
            - content (native-level Spanish, 300-400 words)
            - summary (Spanish, one sentence)
            - reading_time (int, estimated minutes)
            - topic (metadata)
            - sources (metadata, list of source names)
        """
        from scripts import prompts

        prompt = prompts.get_synthesis_prompt(topic, sources)

        self.logger.info(f"Synthesizing base article for topic: {topic['title']}")

        response = self._call_llm(prompt)
        article = self._parse_response(response, topic, sources)

        self.logger.info(f"Synthesized base article: {article['title']}")
        self.logger.debug(f"Base article word count: {len(article['content'].split())}")

        return article

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM with prompt for synthesis"""
        model = self.llm_config['models']['generation']
        max_tokens = self.llm_config.get('max_tokens', 4096)
        provider = self.llm_config['provider']

        try:
            if provider == 'anthropic':
                response = self.llm_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif provider == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            self.logger.error(f"LLM API call failed during synthesis: {e}")
            raise

    def _parse_response(
        self,
        response: str,
        topic: Dict,
        sources: List[Dict]
    ) -> Dict:
        """Parse LLM JSON response into base article dict"""

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
            parsed['sources'] = [s['source'] for s in sources]

            # Validate required fields
            required = ['title', 'content', 'summary', 'reading_time']
            for field in required:
                if field not in parsed:
                    self.logger.error(f"Missing required field in base article: {field}")
                    raise ValueError(f"Missing required field: {field}")

            # Ensure reading_time is an integer
            if not isinstance(parsed['reading_time'], int):
                try:
                    parsed['reading_time'] = int(parsed['reading_time'])
                except (ValueError, TypeError):
                    self.logger.warning("Invalid reading_time, defaulting to 3")
                    parsed['reading_time'] = 3

            return parsed

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse synthesis response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:500]}")
            raise ValueError(f"LLM returned invalid JSON during synthesis: {e}")

        except ValueError as e:
            self.logger.error(f"Invalid base article structure: {e}")
            raise ValueError(f"Invalid base article structure: {e}")

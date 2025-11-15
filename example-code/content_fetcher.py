"""
Content Fetcher Component

Fetches and extracts clean article text from source URLs using Trafilatura.
"""

import requests
import trafilatura
from typing import List, Dict, Optional
from urllib.parse import urlparse
import logging


class ContentFetcher:
    """Fetches and cleans article content from URLs"""
    
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('ContentFetcher')
        self.timeout = config['sources'].get('fetch_timeout', 10)
        self.max_words_per_source = 300
    
    def fetch_topic_sources(self, topic: Dict) -> List[Dict]:
        """
        Fetch clean article text for a topic
        
        Args:
            topic: Topic dict with headlines
        
        Returns:
            List of source content dicts
        """
        sources = []
        urls = [h['url'] for h in topic['headlines'][:8]]  # Try up to 8 sources
        
        self.logger.info(f"Fetching sources for: {topic['title']}")
        
        for url in urls:
            try:
                content = self._fetch_article(url)
                
                if content and len(content['text'].split()) > 100:  # Min 100 words
                    sources.append(content)
                    self.logger.debug(f"✓ Fetched: {urlparse(url).netloc}")
                
                if len(sources) >= 5:  # Enough sources
                    break
            
            except Exception as e:
                self.logger.debug(f"✗ Failed: {urlparse(url).netloc} - {e}")
                continue
        
        self.logger.info(f"Successfully fetched {len(sources)} sources")
        return sources
    
    def _fetch_article(self, url: str) -> Optional[Dict]:
        """
        Fetch and extract clean article text
        
        Uses Trafilatura for robust extraction
        """
        # Special handling for Wikipedia
        if 'wikipedia.org' in url:
            return self._fetch_wikipedia(url)
        
        # Regular article fetch
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; AutoSpanishBot/1.0)'
                }
            )
            response.raise_for_status()
            
            # Extract main content using Trafilatura
            extracted = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )
            
            if not extracted:
                return None
            
            # Get metadata
            metadata = trafilatura.extract_metadata(response.content)
            
            # Truncate to first N words
            words = extracted.split()[:self.max_words_per_source]
            truncated_text = ' '.join(words)
            
            return {
                'url': url,
                'text': truncated_text,
                'title': metadata.title if metadata else '',
                'author': metadata.author if metadata else '',
                'date': metadata.date if metadata else '',
                'source': urlparse(url).netloc,
                'word_count': len(words)
            }
        
        except Exception as e:
            self.logger.debug(f"Fetch error for {url}: {e}")
            return None
    
    def _fetch_wikipedia(self, url: str) -> Optional[Dict]:
        """
        Fetch Wikipedia content via API
        
        Wikipedia has a clean API we can use directly
        """
        try:
            # Extract article title from URL
            # Example: https://es.wikipedia.org/wiki/Lionel_Messi
            parts = url.rstrip('/').split('/')
            title = parts[-1]
            
            # Determine language
            if 'es.wikipedia.org' in url:
                lang = 'es'
            else:
                lang = 'en'
            
            # Use Wikipedia API
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            
            response = requests.get(api_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Truncate to first N words
            words = data['extract'].split()[:self.max_words_per_source]
            truncated_text = ' '.join(words)
            
            return {
                'url': data['content_urls']['desktop']['page'],
                'text': truncated_text,
                'title': data['title'],
                'source': 'Wikipedia',
                'word_count': len(words)
            }
        
        except Exception as e:
            self.logger.debug(f"Wikipedia fetch error: {e}")
            return None

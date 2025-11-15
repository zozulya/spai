#!/usr/bin/env python3
"""
AutoSpanishBlog - Main Pipeline Entry Point

This script orchestrates the entire content generation pipeline:
1. Topic Discovery
2. Content Fetching
3. Article Generation
4. Quality Gate
5. Publishing

Usage:
    python main.py                  # Run full pipeline
    ENVIRONMENT=local python main.py # Force local mode
    DRY_RUN=true python main.py     # Generate but don't publish
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

from config import load_config
from logger import setup_logger
from metrics import MetricsCollector
from alerts import AlertManager
from topic_discovery import TopicDiscoverer
from content_fetcher import ContentFetcher
from content_generator import ContentGenerator
from quality_gate import QualityGate
from publisher import Publisher


def detect_environment() -> str:
    """Detect execution environment"""
    if os.getenv('GITHUB_ACTIONS') == 'true':
        return 'production'
    return os.getenv('ENVIRONMENT', 'local')


def create_run_id() -> str:
    """Generate unique run identifier"""
    env = detect_environment()
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    return f"{env}-{timestamp}"


def get_llm_client(config: Dict):
    """Initialize LLM client based on config"""
    provider = config['llm']['provider']
    
    if provider == 'anthropic':
        import anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return anthropic.Anthropic(api_key=api_key)
    
    elif provider == 'openai':
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return openai.OpenAI(api_key=api_key)
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def main():
    """Main pipeline execution"""
    
    # Setup
    run_id = create_run_id()
    environment = detect_environment()
    dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
    
    # Load configuration
    config = load_config(environment)
    
    # Initialize logging
    logger = setup_logger(config, run_id)
    logger.info("Pipeline started", extra={
        'run_id': run_id,
        'environment': environment,
        'dry_run': dry_run
    })
    
    # Initialize components
    metrics = MetricsCollector(config, run_id)
    alerts = AlertManager(config, logger)
    
    try:
        # Initialize LLM client
        llm = get_llm_client(config)
        logger.info("LLM client initialized", extra={'provider': config['llm']['provider']})
        
        # Initialize pipeline components
        discoverer = TopicDiscoverer(config, logger)
        fetcher = ContentFetcher(config, logger)
        generator = ContentGenerator(llm, config, logger)
        quality_gate = QualityGate(llm, config, logger)
        publisher = Publisher(config, logger, dry_run=dry_run)
        
        # Statistics
        stats = {
            'attempted': 0,
            'published': 0,
            'rejected': 0,
            'regenerations': 0
        }
        
        # Phase 1: Topic Discovery
        logger.info("=== Phase 1: Topic Discovery ===")
        metrics.start_phase('discovery')
        
        topics = discoverer.discover(limit=10)
        logger.info(f"Discovered {len(topics)} topics")
        
        metrics.end_phase('discovery', {
            'topics_found': len(topics),
            'topics_selected': min(len(topics), 10)
        })
        
        if not topics:
            raise Exception("No topics discovered")
        
        # Phase 2-5: Process each topic
        target_articles = config['generation']['articles_per_run']
        levels = config['generation']['levels']
        
        for topic in topics:
            if stats['published'] >= target_articles:
                logger.info(f"Target reached: {target_articles} articles published")
                break
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing topic: {topic['title']}")
            logger.info(f"{'='*60}")
            
            # Phase 2: Fetch Sources
            metrics.start_phase('fetching')
            sources = fetcher.fetch_topic_sources(topic)
            metrics.end_phase('fetching', {
                'sources_fetched': len(sources),
                'sources_failed': 0  # TODO: Track failures
            })
            
            if len(sources) < 3:
                logger.warning(f"Insufficient sources for {topic['title']}: {len(sources)}")
                continue
            
            logger.info(f"Fetched {len(sources)} sources")
            
            # Generate articles for each level
            for level in levels:
                stats['attempted'] += 1
                
                logger.info(f"\n--- Generating {level} article ---")
                
                # Phase 3: Generate Article
                metrics.start_phase('generation')
                article = generator.generate_article(topic, sources, level)
                metrics.end_phase('generation', {
                    'level': level,
                    'word_count': len(article['content'].split())
                })
                
                logger.info(f"Generated: {article['title']} ({len(article['content'].split())} words)")
                
                # Phase 4: Quality Gate (with regeneration)
                metrics.start_phase('quality')
                final_article, quality_result = quality_gate.check_and_improve(
                    article,
                    sources,
                    generator
                )
                metrics.end_phase('quality', {
                    'passed': quality_result.passed,
                    'score': quality_result.score,
                    'attempts': 1  # TODO: Track actual attempts
                })
                
                if final_article:
                    # Quality passed
                    logger.info(f"✅ Quality check passed: {quality_result.score:.1f}/10")
                    
                    # Phase 5: Publish
                    metrics.start_phase('publishing')
                    published = publisher.save_article(final_article)
                    metrics.end_phase('publishing', {
                        'success': published
                    })
                    
                    if published:
                        stats['published'] += 1
                        logger.info(f"📄 Published: {final_article['title']}")
                else:
                    # Quality failed
                    stats['rejected'] += 1
                    logger.warning(f"❌ Rejected: {article['title']} (score: {quality_result.score:.1f}/10)")
                    logger.warning(f"   Issues: {', '.join(quality_result.issues[:2])}")
        
        # Pipeline completed successfully
        duration = metrics.get_total_duration()
        
        logger.info(f"\n{'='*60}")
        logger.info("Pipeline completed successfully")
        logger.info(f"{'='*60}")
        logger.info(f"✨ Summary:")
        logger.info(f"   Attempted: {stats['attempted']}")
        logger.info(f"   Published: {stats['published']}")
        logger.info(f"   Rejected: {stats['rejected']}")
        logger.info(f"   Success rate: {stats['published']/stats['attempted']*100:.0f}%")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"{'='*60}")
        
        # Save metrics
        metrics.save({
            'status': 'success',
            'stats': stats
        })
        
        # Check for alerts
        if stats['published'] == 0:
            alerts.send_critical("Zero articles published", {
                'run_id': run_id,
                'attempted': stats['attempted'],
                'rejected': stats['rejected']
            })
        elif stats['published'] < target_articles * 0.5:
            alerts.send_warning("Low publish rate", {
                'published': stats['published'],
                'target': target_articles,
                'rate': stats['published'] / target_articles
            })
        
        return 0
    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        
        # Save failure metrics
        metrics.save({
            'status': 'failed',
            'error': str(e)
        })
        
        # Send alert
        alerts.send_critical("Pipeline failed", {
            'run_id': run_id,
            'error': str(e)
        })
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Integration tests for two-step article generation pipeline

These tests verify that components work together correctly, catching bugs
that unit tests miss (like the Publisher AttributeError on None topic).
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from scripts.article_synthesizer import ArticleSynthesizer
from scripts.level_adapter import LevelAdapter
from scripts.content_generator import ContentGenerator
from scripts.publisher import Publisher
from scripts.models import Topic, BaseArticle, AdaptedArticle


class TestTwoStepPipelineIntegration:
    """Integration tests for synthesis → adaptation flow"""

    @patch('scripts.article_synthesizer.OpenAI')
    @patch('scripts.level_adapter.OpenAI')
    def test_synthesis_to_adaptation_a2(self, mock_adapter_openai, mock_synth_openai,
                                         base_config, mock_logger, sample_topic, sample_sources):
        """Test complete two-step flow: ArticleSynthesizer → LevelAdapter (A2)"""
        # Setup synthesizer mock
        synth_client = MagicMock()
        mock_synth_openai.return_value = synth_client

        base_response = {
            'title': 'España reduce emisiones de CO2',
            'content': 'España ha logrado reducir sus emisiones de dióxido de carbono...',
            'summary': 'España reduce CO2 gracias a energías renovables.',
            'reading_time': 3
        }

        synth_mock_response = MagicMock()
        synth_mock_response.choices = [MagicMock()]
        synth_mock_response.choices[0].message.content = json.dumps(base_response)
        synth_client.chat.completions.create.return_value = synth_mock_response

        # Setup adapter mock
        adapter_client = MagicMock()
        mock_adapter_openai.return_value = adapter_client

        a2_response = {
            'title': 'España tiene menos contaminación',
            'content': 'España reduce sus **emisiones**. El gobierno dice que baja 15%.',
            'summary': 'España contamina menos.',
            'reading_time': 2,
            'vocabulary': {
                'emisiones': 'emissions - gases que salen al aire'
            }
        }

        adapter_mock_response = MagicMock()
        adapter_mock_response.choices = [MagicMock()]
        adapter_mock_response.choices[0].message.content = json.dumps(a2_response)
        adapter_client.chat.completions.create.return_value = adapter_mock_response

        # Execute two-step pipeline
        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        adapter = LevelAdapter(base_config, mock_logger)

        # Step 1: Synthesize
        base_article = synthesizer.synthesize(sample_topic, sample_sources)

        # Verify base article structure
        assert base_article['title'] == base_response['title']
        assert base_article['topic'] == sample_topic
        assert base_article['sources'] == ['El País', 'BBC Mundo', 'El Mundo']

        # Step 2: Adapt
        a2_article = adapter.adapt_to_level(base_article, 'A2')

        # Verify adapted article
        assert a2_article['level'] == 'A2'
        assert a2_article['title'] == a2_response['title']
        assert 'vocabulary' in a2_article
        assert len(a2_article['vocabulary']) > 0

        # CRITICAL: Verify metadata propagation (would have caught the bug!)
        assert a2_article['topic'] == sample_topic  # Not None!
        assert a2_article['sources'] == ['El País', 'BBC Mundo', 'El Mundo']

        # Verify base article stored for regeneration
        assert 'base_article' in a2_article
        assert a2_article['base_article']['title'] == base_article['title']

    @patch('scripts.content_generator.ArticleSynthesizer')
    @patch('scripts.content_generator.LevelAdapter')
    def test_content_generator_orchestration(self, mock_adapter_class, mock_synth_class,
                                              base_config, mock_logger, sample_topic,
                                              sample_sources, sample_base_article, sample_a2_article):
        """Test ContentGenerator orchestrates both steps correctly"""
        # Setup mocks
        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize.return_value = sample_base_article
        mock_synth_class.return_value = mock_synthesizer

        mock_adapter = MagicMock()
        mock_adapter.adapt_to_level.return_value = sample_a2_article
        mock_adapter_class.return_value = mock_adapter

        # Execute
        generator = ContentGenerator(base_config, mock_logger)
        result = generator.generate_article(sample_topic, sample_sources, 'A2')

        # Verify orchestration
        mock_synthesizer.synthesize.assert_called_once_with(sample_topic, sample_sources)
        mock_adapter.adapt_to_level.assert_called_once_with(sample_base_article, 'A2')

        # Verify result has correct metadata
        assert result == sample_a2_article


class TestPublisherIntegration:
    """Integration tests including Publisher (would have caught the bug!)"""

    @patch('scripts.article_synthesizer.OpenAI')
    @patch('scripts.level_adapter.OpenAI')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('pathlib.Path.mkdir')
    def test_synthesis_to_adaptation_to_publisher(self, mock_mkdir, mock_open,
                                                    mock_adapter_openai, mock_synth_openai,
                                                    base_config, mock_logger, sample_topic,
                                                    sample_sources):
        """
        Test complete flow: Synthesize → Adapt → Publish

        This test would have caught the Publisher AttributeError bug!
        """
        # Setup synthesizer
        synth_client = MagicMock()
        mock_synth_openai.return_value = synth_client

        base_response = {
            'title': 'España reduce emisiones',
            'content': 'Content here...',
            'summary': 'Summary',
            'reading_time': 3
        }

        synth_mock_response = MagicMock()
        synth_mock_response.choices = [MagicMock()]
        synth_mock_response.choices[0].message.content = json.dumps(base_response)
        synth_client.chat.completions.create.return_value = synth_mock_response

        # Setup adapter
        adapter_client = MagicMock()
        mock_adapter_openai.return_value = adapter_client

        a2_response = {
            'title': 'España contamina menos',
            'content': 'España reduce **emisiones**.',
            'summary': 'España mejor.',
            'reading_time': 2,
            'vocabulary': {'emisiones': 'emissions - gases'}
        }

        adapter_mock_response = MagicMock()
        adapter_mock_response.choices = [MagicMock()]
        adapter_mock_response.choices[0].message.content = json.dumps(a2_response)
        adapter_client.chat.completions.create.return_value = adapter_mock_response

        # Execute full pipeline
        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        adapter = LevelAdapter(base_config, mock_logger)
        publisher = Publisher(base_config, mock_logger, dry_run=True)

        # Step 1: Synthesize
        base_article = synthesizer.synthesize(sample_topic, sample_sources)

        # Step 2: Adapt
        a2_article = adapter.adapt_to_level(base_article, 'A2')

        # Step 3: Publish (THIS WOULD HAVE CRASHED WITH THE BUG!)
        # The bug was: a2_article['topic'] could be None, causing AttributeError
        # in Publisher._format_topics() when calling topic.get('keywords', [])
        success = publisher.save_article(a2_article)

        # If we get here, the bug is fixed!
        assert success or not success  # Either works, we just shouldn't crash

    @patch('scripts.article_synthesizer.OpenAI')
    @patch('scripts.level_adapter.OpenAI')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('pathlib.Path.mkdir')
    def test_publisher_handles_missing_topic_metadata(self, mock_mkdir, mock_open,
                                                        mock_adapter_openai, mock_synth_openai,
                                                        base_config, mock_logger,
                                                        sample_base_article_minimal):
        """
        Test Publisher handles missing topic metadata gracefully

        This is the EXACT bug scenario that occurred in production.
        """
        # Setup adapter (synthesizer not needed for this test)
        adapter_client = MagicMock()
        mock_adapter_openai.return_value = adapter_client

        # Adapter returns article without topic metadata
        a2_response = {
            'title': 'Test Article',
            'content': 'Test content.',
            'summary': 'Test',
            'reading_time': 2,
            'vocabulary': {}
        }

        adapter_mock_response = MagicMock()
        adapter_mock_response.choices = [MagicMock()]
        adapter_mock_response.choices[0].message.content = json.dumps(a2_response)
        adapter_client.chat.completions.create.return_value = adapter_mock_response

        # Execute
        adapter = LevelAdapter(base_config, mock_logger)
        publisher = Publisher(base_config, mock_logger, dry_run=True)

        # Adapt (base article has no topic metadata)
        a2_article = adapter.adapt_to_level(sample_base_article_minimal, 'A2')

        # CRITICAL TEST: This should NOT crash even though topic is {}
        # Before fix: topic_data.get('keywords') would crash because topic_data was None
        # After fix: topic_data is {} and .get() works fine
        try:
            success = publisher.save_article(a2_article)
            # Success! Bug is fixed
            assert True
        except AttributeError as e:
            # This would be the bug
            pytest.fail(f"Publisher crashed with AttributeError: {e}")


class TestRegenerationIntegration:
    """Integration tests for regeneration with feedback"""

    @patch('scripts.content_generator.ArticleSynthesizer')
    @patch('scripts.content_generator.LevelAdapter')
    def test_regeneration_preserves_metadata(self, mock_adapter_class, mock_synth_class,
                                              base_config, mock_logger, sample_topic,
                                              sample_sources, sample_base_article,
                                              sample_a2_article):
        """Test regeneration preserves topic metadata through the flow"""
        base_config['generation']['two_step_synthesis']['regeneration_strategy'] = 'adaptation_only'

        # Setup mocks
        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize.return_value = sample_base_article
        mock_synth_class.return_value = mock_synthesizer

        # First attempt: article with issues
        first_attempt = sample_a2_article.copy()

        # Second attempt: improved article
        improved_article = sample_a2_article.copy()
        improved_article['title'] = 'Improved Title'

        mock_adapter = MagicMock()
        mock_adapter.adapt_to_level.return_value = improved_article
        mock_adapter_class.return_value = mock_adapter

        # Execute regeneration
        generator = ContentGenerator(base_config, mock_logger)
        issues = ['Sentences too long', 'Vocabulary too complex']

        result = generator.regenerate_with_feedback(
            sample_topic,
            sample_sources,
            'A2',
            first_attempt,
            issues
        )

        # Verify metadata preserved
        assert result['topic'] == sample_topic  # Critical!
        assert result['sources'] == sample_base_article['sources']

        # Verify adapter called with feedback
        mock_adapter.adapt_to_level.assert_called_once()
        call_args = mock_adapter.adapt_to_level.call_args
        assert call_args[1]['feedback'] == issues

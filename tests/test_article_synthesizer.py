"""
Unit tests for ArticleSynthesizer component
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from scripts.article_synthesizer import ArticleSynthesizer


class TestArticleSynthesizerInit:
    """Test ArticleSynthesizer initialization"""

    def test_init_with_openai(self, base_config, mock_logger):
        """Test initialization with OpenAI provider"""
        with patch('scripts.article_synthesizer.OpenAI'):
            synthesizer = ArticleSynthesizer(base_config, mock_logger)

            assert synthesizer.config == base_config
            assert synthesizer.llm_config == base_config['llm']
            mock_logger.getChild.assert_called_with('ArticleSynthesizer')

    def test_init_with_anthropic(self, base_config, mock_logger):
        """Test initialization with Anthropic provider"""
        base_config['llm']['provider'] = 'anthropic'
        base_config['llm']['anthropic_api_key'] = 'test-key'

        with patch('scripts.article_synthesizer.Anthropic'):
            synthesizer = ArticleSynthesizer(base_config, mock_logger)

            assert synthesizer.llm_config['provider'] == 'anthropic'

    def test_init_missing_api_key_openai(self, base_config, mock_logger):
        """Test initialization fails with missing OpenAI API key"""
        del base_config['llm']['openai_api_key']

        with pytest.raises(ValueError, match="Missing OPENAI_API_KEY"):
            ArticleSynthesizer(base_config, mock_logger)

    def test_init_missing_api_key_anthropic(self, base_config, mock_logger):
        """Test initialization fails with missing Anthropic API key"""
        base_config['llm']['provider'] = 'anthropic'

        with pytest.raises(ValueError, match="Missing ANTHROPIC_API_KEY"):
            ArticleSynthesizer(base_config, mock_logger)

    def test_init_unknown_provider(self, base_config, mock_logger):
        """Test initialization fails with unknown provider"""
        base_config['llm']['provider'] = 'unknown'

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            ArticleSynthesizer(base_config, mock_logger)


class TestArticleSynthesizerSynthesize:
    """Test synthesis functionality"""

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_success(self, mock_openai, base_config, mock_logger,
                                 sample_topic, sample_sources, sample_base_article):
        """Test successful article synthesis"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(sample_base_article)
        mock_client.chat.completions.create.return_value = mock_response

        # Create synthesizer and synthesize
        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        # Verify
        assert result['title'] == sample_base_article['title']
        assert result['content'] == sample_base_article['content']
        assert result['summary'] == sample_base_article['summary']
        assert result['reading_time'] == sample_base_article['reading_time']
        assert result['topic'] == sample_topic
        assert result['sources'] == ['El País', 'BBC Mundo', 'El Mundo']

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'gpt-4o'
        assert call_kwargs['temperature'] == 0.3

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_with_markdown_json(self, mock_openai, base_config, mock_logger,
                                            sample_topic, sample_sources, sample_base_article):
        """Test synthesis with JSON wrapped in markdown code blocks"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock response with markdown wrapper
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"```json\n{json.dumps(sample_base_article)}\n```"
        mock_client.chat.completions.create.return_value = mock_response

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        # Should still parse correctly
        assert result['title'] == sample_base_article['title']
        assert 'topic' in result
        assert 'sources' in result

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_missing_required_field(self, mock_openai, base_config, mock_logger,
                                                 sample_topic, sample_sources):
        """Test synthesis fails when required field is missing"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Response missing 'summary'
        incomplete_response = {
            'title': 'Test',
            'content': 'Content',
            'reading_time': 2
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(incomplete_response)
        mock_client.chat.completions.create.return_value = mock_response

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(ValueError, match="Missing required field"):
            synthesizer.synthesize(sample_topic, sample_sources)

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_invalid_json(self, mock_openai, base_config, mock_logger,
                                      sample_topic, sample_sources):
        """Test synthesis fails with invalid JSON"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON at all"
        mock_client.chat.completions.create.return_value = mock_response

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(ValueError, match="LLM returned invalid JSON"):
            synthesizer.synthesize(sample_topic, sample_sources)

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_reading_time_conversion(self, mock_openai, base_config, mock_logger,
                                                  sample_topic, sample_sources):
        """Test reading_time is converted to int"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Response with string reading_time
        response = {
            'title': 'Test',
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': '3'  # String instead of int
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response)
        mock_client.chat.completions.create.return_value = mock_response

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        assert isinstance(result['reading_time'], int)
        assert result['reading_time'] == 3

    @patch('scripts.article_synthesizer.OpenAI')
    def test_synthesize_llm_api_error(self, mock_openai, base_config, mock_logger,
                                       sample_topic, sample_sources):
        """Test synthesis handles LLM API errors"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Simulate API error
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(Exception, match="API Error"):
            synthesizer.synthesize(sample_topic, sample_sources)


class TestArticleSynthesizerAnthropic:
    """Test Anthropic-specific functionality"""

    @patch('scripts.article_synthesizer.Anthropic')
    def test_synthesize_with_anthropic(self, mock_anthropic, base_config, mock_logger,
                                        sample_topic, sample_sources, sample_base_article):
        """Test synthesis with Anthropic provider"""
        base_config['llm']['provider'] = 'anthropic'
        base_config['llm']['anthropic_api_key'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(sample_base_article)
        mock_client.messages.create.return_value = mock_response

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        assert result['title'] == sample_base_article['title']
        mock_client.messages.create.assert_called_once()

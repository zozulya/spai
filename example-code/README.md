# AutoSpanishBlog - Python Implementation

Complete Python implementation of the AutoSpanishBlog system for automated Spanish language learning content generation.

## 📁 Project Structure

```
autospanishblog/
├── scripts/
│   ├── main.py                    # Main pipeline entry point
│   ├── config.py                  # Configuration management
│   ├── logger.py                  # Structured logging
│   ├── metrics.py                 # Metrics collection
│   ├── alerts.py                  # Alert management
│   ├── topic_discovery.py         # Topic discovery with SpaCy
│   ├── content_fetcher.py         # Content fetching with Trafilatura
│   ├── content_generator.py       # LLM article generation
│   ├── quality_gate.py            # Quality checking
│   └── publisher.py               # Jekyll markdown output
│
├── config/
│   ├── base.yaml                  # Base configuration
│   ├── local.yaml                 # Local development overrides
│   └── production.yaml            # Production overrides
│
├── output/                        # Generated content (gitignore)
│   ├── _posts/                    # Jekyll articles
│   ├── logs/                      # Production logs
│   └── metrics/                   # Metrics data
│
├── logs/                          # Local development logs (gitignore)
│
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
├── Makefile                       # Development commands
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- API keys:
  - Anthropic API key (for Claude)
  - OR OpenAI API key (for GPT)

### Setup

1. **Clone the repository** (or create these files)

2. **Set up environment variables:**

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
# OR
export OPENAI_API_KEY="your-openai-key-here"
```

3. **Build the Docker container:**

```bash
make build
# OR
docker compose build
```

4. **Run the pipeline:**

```bash
make run
# OR
docker compose run generator
```

### First Run

On first run, the system will:
1. Discover topics from 30+ Spanish sources
2. Generate 2 articles (A2 + B1 levels)
3. Run quality checks with regeneration
4. Save approved articles to `output/_posts/`
5. Log everything to `logs/local.log`

**Expected duration:** 5-10 minutes for 2 articles

## 💻 Development Commands

### Run full pipeline
```bash
make run
```

### Dry run (generate but don't save)
```bash
make dry-run
```

### Test topic discovery only
```bash
make test-discovery
```

### View logs in real-time
```bash
make logs
```

### Clean generated files
```bash
make clean
```

### Override articles per run
```bash
ARTICLES=1 make run
```

## 📋 Configuration

Configuration is hierarchical:
```
base.yaml → {local|production}.yaml → Environment Variables → Final Config
```

### Edit Configuration

Edit `config/local.yaml` for development settings:

```yaml
generation:
  articles_per_run: 2  # Number of articles to generate

quality_gate:
  min_score: 7.5       # Minimum quality score (0-10)
  max_attempts: 3      # Max regeneration attempts
```

### Environment Variables

Override any config via environment variables:

```bash
export ARTICLES_PER_RUN=1
export ENVIRONMENT=production
```

## 🧪 Testing Individual Components

### Test Topic Discovery

```bash
docker compose run generator python -c "
from scripts.topic_discovery import TopicDiscoverer
from scripts.config import load_config
from scripts.logger import setup_logger

config = load_config('local')
logger = setup_logger(config, 'test')
discoverer = TopicDiscoverer(config, logger)
topics = discoverer.discover(10)

for topic in topics:
    print(f'{topic[\"title\"]} (score: {topic[\"score\"]})')
"
```

### Test Content Fetcher

```python
from scripts.content_fetcher import ContentFetcher
from scripts.config import load_config
from scripts.logger import setup_logger

config = load_config('local')
logger = setup_logger(config, 'test')
fetcher = ContentFetcher(config, logger)

# Mock topic with headlines
topic = {
    'title': 'Test Topic',
    'headlines': [
        {'url': 'https://elpais.com/...', 'text': 'Headline'}
    ]
}

sources = fetcher.fetch_topic_sources(topic)
print(f"Fetched {len(sources)} sources")
```

## 📊 Understanding the Output

### Article Files

Generated articles are saved to `output/_posts/`:

```
output/_posts/2025-11-11-messi-estados-unidos-a2.md
output/_posts/2025-11-11-messi-estados-unidos-b1.md
```

Each file contains:
- YAML frontmatter (metadata)
- Article content in Spanish
- Vocabulary section
- Attribution

### Log Files

**Local development:** `logs/local.log`
- Human-readable colored output
- DEBUG level logging

**Production:** `output/logs/production.log`
- JSON structured logging
- INFO level logging

### Metrics

**Per-run metrics:** `output/metrics/<run-id>.json`

Contains:
- Phase durations
- Articles generated/rejected
- Quality scores
- Cost estimates
- Errors

**Summary:** `output/metrics/summary.json`

Rolling 30-day summary:
- Total runs
- Success rate
- Total articles
- Total cost

## 🔧 Troubleshooting

### SpaCy Model Not Found

```bash
docker compose run generator python -m spacy download es_core_news_sm
```

### API Key Issues

Verify your key is set:
```bash
echo $ANTHROPIC_API_KEY
```

Or pass directly:
```bash
ANTHROPIC_API_KEY=sk-... make run
```

### No Topics Found

Check source accessibility:
```bash
make test-discovery
```

If sources are blocked:
- Check network connectivity
- Some sources may be geo-restricted
- RSS feeds may be temporarily down

### Articles Failing Quality Gate

View rejection log:
```bash
cat output/logs/rejections.jsonl | jq
```

Common issues:
- Grammar errors → Adjust prompts
- Wrong vocabulary level → Update level rules
- Too similar to sources → Check truncation

Lower quality threshold temporarily:
```yaml
# config/local.yaml
quality_gate:
  min_score: 6.5  # Lower for testing
```

## 📈 Monitoring

### View Health Status

```bash
cat output/health.json
```

### Check Recent Runs

```bash
cat output/metrics/summary.json | jq
```

### Analyze Quality Trends

```python
import json
from pathlib import Path

metrics_dir = Path('output/metrics')
scores = []

for file in metrics_dir.glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        if 'quality' in data.get('phases', {}):
            scores.append(data['phases']['quality']['data'].get('avg_score', 0))

if scores:
    print(f"Average quality: {sum(scores)/len(scores):.1f}/10")
```

## 🚀 Production Deployment

### Set Environment to Production

```bash
export ENVIRONMENT=production
export ANTHROPIC_API_KEY=your-prod-key
export ALERT_EMAIL=your@email.com
```

### Run Once

```bash
docker compose run generator
```

### Expected Production Output

```
Pipeline started
Found 15 topics
Processing: Lionel Messi
  ✅ A2 passed (7.9)
  ✅ B1 passed (7.7)
Processing: Copa América
  ✅ A2 passed (8.1)
  🔄 B1 regenerating (6.8)
  ✅ B1 passed (7.6)
...
Summary:
  Published: 4/4 (100%)
  Avg quality: 7.9
  Duration: 8m 23s
  Cost: $0.12
```

## 🔐 Security Notes

**Never commit:**
- API keys
- `config/secrets.yaml`
- `.env` files

**Always:**
- Use environment variables for secrets
- Use GitHub Secrets in CI/CD
- Rotate keys regularly

## 📖 Component Documentation

### main.py
Entry point that orchestrates the entire pipeline. Handles environment detection, component initialization, and error handling.

### topic_discovery.py
Discovers topics using:
- RSS feeds from 30+ Spanish sources
- SpaCy Spanish NER for entity extraction
- Cross-source validation (3+ sources required)
- Learner-friendliness scoring

### content_fetcher.py
Fetches clean article text using:
- Trafilatura for robust extraction
- Wikipedia API for Wikipedia articles
- Truncation to 300 words per source
- Error handling and retries

### content_generator.py
Generates articles using LLM:
- A2 and B1 level support
- Multi-source synthesis prompts
- Structured JSON output
- Regeneration with feedback

### quality_gate.py
Ensures quality:
- LLM judge scoring (0-10)
- 7.5+ minimum score
- Up to 3 regeneration attempts
- Issue-specific feedback

### publisher.py
Saves as Jekyll markdown:
- YAML frontmatter
- Vocabulary sections
- Attribution
- SEO-friendly slugs

## 🎯 Next Steps

1. **Run locally** to verify everything works
2. **Adjust prompts** in `content_generator.py` based on output
3. **Tune quality threshold** in `config/base.yaml`
4. **Set up GitHub Actions** for automated runs
5. **Deploy to production** with environment variables

## 📝 License

See LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please:
1. Test changes locally
2. Update documentation
3. Follow existing code style
4. Add tests for new features

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Check troubleshooting section above
- Review logs in `logs/` directory

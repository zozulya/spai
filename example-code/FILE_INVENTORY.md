# AutoSpanishBlog - File Inventory

This document lists all Python implementation files created and their purposes.

## 📄 Core Python Scripts (scripts/)

### main.py
**Purpose:** Pipeline orchestration and entry point
**Key Functions:**
- `main()` - Orchestrates full pipeline execution
- `detect_environment()` - Detects local vs production
- `create_run_id()` - Generates unique run identifier
- `get_llm_client()` - Initializes Anthropic or OpenAI client

**Dependencies:** All other scripts
**Called by:** Docker container, manual execution

---

### config.py
**Purpose:** Hierarchical configuration management
**Key Functions:**
- `load_config(environment)` - Loads and merges configs
- `deep_merge(base, override)` - Deep merges dictionaries
- `apply_env_overrides(config)` - Applies environment variables

**Dependencies:** pyyaml
**Called by:** main.py

---

### logger.py
**Purpose:** Structured logging with environment awareness
**Key Classes:**
- `JSONFormatter` - JSON logs for production
- `ColoredFormatter` - Human-readable logs for development

**Key Functions:**
- `setup_logger(config, run_id)` - Configures logging

**Dependencies:** logging (stdlib)
**Called by:** main.py

---

### metrics.py
**Purpose:** Performance and cost tracking
**Key Classes:**
- `MetricsCollector` - Collects and saves metrics

**Key Methods:**
- `start_phase(name)` - Begin timing a phase
- `end_phase(name, data)` - End timing and record data
- `record_cost(usd)` - Track LLM costs
- `save()` - Save metrics to JSON

**Dependencies:** json, datetime
**Called by:** main.py

---

### alerts.py
**Purpose:** Alert management with cooldown
**Key Classes:**
- `AlertManager` - Sends alerts via email/Telegram

**Key Methods:**
- `send_critical(msg, context)` - Critical alerts (no cooldown)
- `send_error(msg, context)` - Error alerts (with cooldown)
- `send_warning(msg, context)` - Warning alerts (daily digest)

**Dependencies:** smtplib, requests (for Telegram)
**Called by:** main.py

---

### topic_discovery.py
**Purpose:** Discover newsworthy topics from multiple sources
**Key Classes:**
- `TopicDiscoverer` - Topic discovery engine

**Key Methods:**
- `discover(limit)` - Main entry point
- `_fetch_source(source)` - Fetch from one source
- `_extract_entities(text)` - SpaCy NER extraction
- `_cluster_topics(entities)` - Find cross-source topics
- `_rank_topics(topics)` - Score by learnability

**Dependencies:** spacy, feedparser, requests
**Called by:** main.py
**Features:**
- 30+ source support (RSS, Wikipedia, Google Trends)
- SpaCy Spanish NER
- Cross-source validation (3+ sources required)
- Learner-friendly scoring

---

### content_fetcher.py
**Purpose:** Extract clean article text from URLs
**Key Classes:**
- `ContentFetcher` - Content extraction engine

**Key Methods:**
- `fetch_topic_sources(topic)` - Fetch multiple sources
- `_fetch_article(url)` - Extract clean text
- `_fetch_wikipedia(url)` - Special Wikipedia handling

**Dependencies:** trafilatura, requests
**Called by:** main.py
**Features:**
- Trafilatura for robust extraction
- 300-word truncation per source
- Special Wikipedia API handling
- Error handling and retries

---

### content_generator.py
**Purpose:** Generate original Spanish articles via LLM
**Key Classes:**
- `ContentGenerator` - Article generation engine

**Key Methods:**
- `generate_article(topic, sources, level)` - Initial generation
- `regenerate_with_feedback(...)` - Regenerate with issues
- `_build_prompt(...)` - Build LLM prompt
- `_call_llm(prompt)` - Call Anthropic/OpenAI
- `_parse_response(response)` - Parse JSON output

**Dependencies:** anthropic or openai, json
**Called by:** main.py, quality_gate.py (for regeneration)
**Features:**
- A2 and B1 level support
- Multi-source synthesis prompts
- Structured JSON output
- Feedback-aware regeneration

---

### quality_gate.py
**Purpose:** Evaluate and improve article quality
**Key Classes:**
- `QualityGate` - Quality evaluation engine
- `QualityResult` - Result dataclass

**Key Methods:**
- `check_and_improve(article, sources, generator)` - Main check
- `_evaluate(article)` - Score article
- `_build_judge_prompt(article)` - Build evaluation prompt
- `_parse_judge_response(response)` - Parse judge output

**Dependencies:** anthropic or openai, json
**Called by:** main.py
**Features:**
- LLM judge scoring (0-10 points)
- 7.5+ minimum threshold
- Up to 3 regeneration attempts
- Specific issue feedback

---

### publisher.py
**Purpose:** Save articles as Jekyll markdown
**Key Classes:**
- `Publisher` - Jekyll markdown generator

**Key Methods:**
- `save_article(article)` - Save to markdown
- `_generate_filename(article)` - Create Jekyll filename
- `_slugify(text)` - Convert to URL-safe slug
- `_generate_markdown(article)` - Create full markdown

**Dependencies:** pathlib, re, datetime
**Called by:** main.py
**Features:**
- YAML frontmatter generation
- Vocabulary section formatting
- Attribution section
- SEO-friendly slugs

---

## 📋 Configuration Files (config/)

### base.yaml
**Purpose:** Shared configuration for all environments
**Contains:**
- Source settings
- Article generation parameters
- Quality gate thresholds
- LLM configuration
- Default logging/metrics/alerts

---

### local.yaml
**Purpose:** Development environment overrides
**Contains:**
- Console logging (colored)
- DEBUG level
- Fewer articles per run (faster testing)
- Disabled metrics and alerts

---

### production.yaml
**Purpose:** Production environment overrides
**Contains:**
- JSON structured logging
- INFO level
- Full article generation
- Enabled metrics and alerts
- Email/Telegram configuration

---

### sources-example.yaml
**Purpose:** Example source configurations
**Contains:**
- 30+ RSS feed URLs
- Wikipedia trending config
- Google Trends configs
- Categorized sources

---

## 🐳 Docker Files

### Dockerfile
**Purpose:** Container definition
**Features:**
- Python 3.11 slim base
- SpaCy model installation
- Non-root user
- Multi-stage caching

---

### docker-compose.yml
**Purpose:** Container orchestration
**Features:**
- Volume mounts
- Environment variable passing
- Command override support

---

## 🛠️ Development Files

### Makefile
**Purpose:** Development convenience commands
**Commands:**
- `make run` - Run full pipeline
- `make dry-run` - Generate without saving
- `make test-discovery` - Test topic discovery
- `make logs` - Tail logs
- `make clean` - Clean generated files

---

### requirements.txt
**Purpose:** Python dependency specification
**Key Dependencies:**
- anthropic / openai (LLM)
- spacy (NER)
- trafilatura (extraction)
- feedparser (RSS)
- requests (HTTP)

---

## 📖 Documentation

### README.md
**Purpose:** Complete usage documentation
**Sections:**
- Quick start guide
- Configuration instructions
- Development commands
- Troubleshooting
- Production deployment
- Component documentation

---

### autospanishblog-system-design.md
**Purpose:** Complete system design document
**Sections:**
- Architecture overview
- Component specifications
- Implementation roadmap
- Cost analysis
- Technical specifications

---

## 📊 Output Structure

### output/_posts/
**Generated:** Jekyll markdown files
**Format:** `YYYY-MM-DD-title-slug-level.md`
**Contains:** Articles with frontmatter, content, vocabulary

---

### output/logs/
**Generated:** Production log files
**Format:** JSON structured logs
**Contains:** Pipeline execution logs, rejections

---

### output/metrics/
**Generated:** Performance metrics
**Files:**
- `{run-id}.json` - Per-run metrics
- `summary.json` - Rolling 30-day summary
**Contains:** Durations, costs, quality scores

---

### logs/
**Generated:** Local development logs
**Format:** Human-readable colored logs
**Contains:** DEBUG level execution traces

---

## 🔄 Execution Flow

```
1. main.py
   ↓
2. config.py → Load configuration
   ↓
3. logger.py → Setup logging
   ↓
4. topic_discovery.py → Find topics
   ↓
5. content_fetcher.py → Get sources
   ↓
6. content_generator.py → Generate articles
   ↓
7. quality_gate.py → Check quality
   ↓ (if failed)
   content_generator.py → Regenerate
   ↓ (loop up to 3x)
8. publisher.py → Save articles
   ↓
9. metrics.py → Save metrics
   ↓
10. alerts.py → Send alerts (if needed)
```

---

## 📦 File Count Summary

**Total Files Created:** 20

**By Category:**
- Python Scripts: 10
- Configuration: 4
- Docker: 2
- Development: 2
- Documentation: 2

**Total Lines of Code:** ~3,500 lines

---

## ✅ Completeness Check

All files from the system design document have been implemented:

- ✅ Main pipeline orchestration
- ✅ Configuration management
- ✅ Logging system
- ✅ Metrics collection
- ✅ Alert management
- ✅ Topic discovery (SpaCy + multi-source)
- ✅ Content fetching (Trafilatura)
- ✅ Content generation (LLM with feedback)
- ✅ Quality gate (LLM judge + regeneration)
- ✅ Publishing (Jekyll markdown)
- ✅ Docker containerization
- ✅ Development tools
- ✅ Documentation

---

## 🚀 Ready to Use

All files are production-ready and can be deployed immediately:

1. Set API keys
2. Run `make build`
3. Run `make run`
4. Articles generated in `output/_posts/`

No additional code needed!

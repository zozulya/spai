.PHONY: help build run test-discovery clean logs

help:
	@echo "AutoSpanishBlog - Development Commands"
	@echo ""
	@echo "  make build           - Build Docker container"
	@echo "  make run             - Run full pipeline"
	@echo "  make dry-run         - Run without saving articles"
	@echo "  make test-discovery  - Test topic discovery only"
	@echo "  make logs            - Tail local logs"
	@echo "  make clean           - Clean generated files"
	@echo ""
	@echo "Environment variables:"
	@echo "  ARTICLES=2           - Override articles per run"
	@echo "  DRY_RUN=true         - Generate but don't save"
	@echo ""

build:
	docker compose build

run:
	docker compose run generator

dry-run:
	DRY_RUN=true docker compose run generator

test-discovery:
	docker compose run generator python -c "\
		from scripts.topic_discovery import TopicDiscoverer; \
		from scripts.config import load_config; \
		from scripts.logger import setup_logger; \
		config = load_config('local'); \
		logger = setup_logger(config, 'test'); \
		discoverer = TopicDiscoverer(config, logger); \
		topics = discoverer.discover(5); \
		print(f'Found {len(topics)} topics'); \
		for t in topics: print(f'  - {t[\"title\"]} (score: {t[\"score\"]})')"

logs:
	tail -f logs/local.log

clean:
	rm -rf logs/*.log
	rm -rf output/_posts/*
	rm -rf output/logs/*
	rm -rf output/metrics/*
	@echo "Cleaned generated files"

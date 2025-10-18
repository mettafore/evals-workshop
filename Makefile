.DEFAULT_GOAL := help

PYTHON := uv run python

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

ruff-check: ## Run Ruff lint checks
	uv run ruff check

ruff-fix: ## Auto-fix lint issues with Ruff
	uv run ruff check --fix

format: ## Format code with Ruff formatter
	uv run ruff format

format-check: ## Verify formatting without changes
	uv run ruff format --check

annotate: ## Launch annotation UI
	uv run python tools/email_annotation_app.py

clear: ## Clear annotations via helper script
	uv run python tools/clear_annotations.py

email-viewer: ## Launch interactive email viewer (optional ARGS="--auto-save")
	$(PYTHON) tools/email_viewer.py $(ARGS)

synthetic-demo: ## Generate coherence dataset (ARGS passes extra flags)
	$(PYTHON) tools/generate_synthetic.py $(ARGS)

.PHONY: help ruff-check ruff-fix format format-check annotate clear email-viewer synthetic-demo

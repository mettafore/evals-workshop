ruff-check:
	uv run ruff check

ruff-fix:
	uv run ruff check --fix

format:
	uv run ruff format

format-check:
	uv run ruff format --check

annotate:
	uv run python tools/email_annotation_app.py


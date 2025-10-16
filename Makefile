ruff-check:
	uv run ruff check --exclude '*.ipynb'

ruff-fix:
	uv run ruff check --fix

format:
	uv run ruff format

format-check:
	uv run ruff format --check --exclude '*.ipynb'



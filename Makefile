.PHONY: install run test lint format notebook

install:  ## Install the package with dev dependencies
	pip install -e ".[dev]"

run:  ## Download data (first run), run every SQL analysis, cluster customers, draw figures
	retail run

notebook:  ## Re-run the report notebook
	jupyter nbconvert --to notebook --execute --inplace notebooks/customer_analytics_report.ipynb

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff check --fix src tests
	ruff format src tests

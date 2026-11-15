# Job Watcher

An installable daily job-market watchlist for finance, banking, lending, wealth management, real estate finance, and mission-driven financial roles.

This project is intentionally separate from the `fda-python` course repository. The site is designed to feel like a calm daily briefing: useful enough to open every morning, polished enough to publish, and flexible enough to follow several career directions while the watchlist evolves.

## Current checkpoint

The first checkpoint includes:

- `site/index.html` — Today page
- `site/browse.html` — searchable open-posting browser with stars saved in the browser
- `site/market.html` — history-driven market report with six chart sections
- a shared visual system, responsive layout, installable manifest, and offline service worker
- a demo dataset at the required fixed paths so the site is useful before the first GitHub Actions run

The demo seed is clearly labeled in the interface. The first successful pipeline run will replace it with source-backed data.

## Watchlist direction

The initial role family is deliberately broad:

- commercial and community banking
- commercial lending and credit
- wealth management and financial planning
- financial analyst and risk roles
- commercial real estate finance
- affordable housing and community-development finance

The current title rule marks a posting as `in_role` when its title contains one of the finance-track phrases in `jobwatcher/title_rules.py`. The browse page still supports viewing every posting returned by the watched employers, so the watchlist can remain exploratory while the primary category is refined.

## Local preview

From this repository root:

```text
uv run python -m http.server 8000 --directory site
```

Open `http://localhost:8000/` in a browser. Opening the HTML files through a local server is required because the pages load `data/history.csv` and `data/status.json` with `fetch`.

## Required pipeline files

The pipeline will keep these files at fixed paths:

- `data/history.csv` — one row per posting
- `data/status.json` — latest run, source health, and daily counts
- `data/raw/<UTC date>/<source>.json.gz` — compressed source responses

Raw responses are the source of truth for rebuilding history. A failed source does not stop the run and produces no raw file for that source/date.

## Build history

The deterministic history builder will be run with:

```text
uv run python scripts/build_history.py
```

## Tests

```text
uv run pytest
```

GitHub Actions will run the tests on every push and the daily pipeline on a UTC schedule. The assignment dates and first-run deadline should be added from Blackboard before the repository is submitted.

The Pages workflow publishes the `site/` folder. The pipeline keeps the required source-of-truth files in `data/` and synchronizes deployment copies to `site/data/` before committing.

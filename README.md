# Job Watcher

[![Tests](https://github.com/trj2004/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/trj2004/job-watcher/actions/workflows/tests.yml)

An installable daily job-market watchlist for finance, banking, lending, wealth management, real estate finance, and mission-driven financial roles.

This project is intentionally separate from the `fda-python` course repository. The site is designed to feel like a calm daily briefing: useful enough to open every morning, polished enough to publish, and flexible enough to follow several career directions while the watchlist evolves.

## Current checkpoint

The first checkpoint includes:

- `site/index.html` — Today page
- `site/browse.html` — searchable open-posting browser with stars saved in the browser
- `site/market.html` — history-driven market report with six chart sections
- `site/career-fit.html` — 12-question reflection quiz that maps answers to exploratory career lanes
- a shared visual system, responsive layout, installable manifest, and offline service worker
- a demo dataset at the required fixed paths so the site is useful before the first GitHub Actions run

The demo seed is clearly labeled in the interface. The first successful pipeline run will replace it with source-backed data.

The first live collection completed across the original source set, but that set was too concentrated in fintech employers. The active watchlist is now being rebuilt in place around conventional banking, lending, wealth management, investment management, commercial real estate, and mission-driven finance employers. The Browse page defaults to Dallas/DFW locations first while keeping nationwide and remote opportunities available.

## Watchlist direction

The initial role family is deliberately broad:

- commercial and community banking
- commercial lending and credit
- wealth management and financial planning
- financial analyst and risk roles
- commercial real estate finance
- affordable housing and community-development finance

The current title rule marks a posting as `in_role` when its title contains one of the finance-track phrases in `jobwatcher/title_rules.py`. The browse page still supports viewing every posting returned by the watched employers, so the watchlist can remain exploratory while the primary category is refined.

Browse also derives an estimated experience label from common title language such as intern, analyst, associate, manager, senior, and vice president. Location filters normalize common ATS variants and are populated from the current open-posting view, so empty or duplicate choices do not clutter the menu.

The Browse cards surface the fields available in the feed before the application link: track, estimated experience, DFW signal, location, team, posted date when supplied, and first-seen age. Long result sets are shown in readable batches with a load-more control. The Career Fit page is a lightweight reflection tool, not a hiring assessment; it suggests adjacent paths such as banking, wealth advice, credit, investments, real estate, and finance strategy.

The active source set includes Texas Capital Bank, Frost Bank, Ares Management, Bain Capital, Blackstone, JLL, State Street, Capital One, LPL Financial, JPMorgan Chase, Newmark, Edward Jones, Morgan Stanley, Climate First Bank, and Invesco. Sources are read from public ATS JSON endpoints; the project does not require employer logins and does not scrape HTML job pages. Old source snapshots remain in git history for traceability but are excluded from the current history build when they are no longer configured.

## Source adapters

| Employer | Applicant tracking system |
| --- | --- |
| Texas Capital Bank | Workday |
| Frost Bank | Workday |
| Ares Management | Workday |
| Bain Capital | Workday |
| Blackstone | Workday |
| JLL | Workday |
| State Street | Workday |
| Capital One | Workday |
| LPL Financial | Workday |
| JPMorgan Chase | Oracle Recruiting |
| Newmark | Oracle Recruiting |
| Edward Jones | MCloud |
| Morgan Stanley | Eightfold |
| Climate First Bank | Greenhouse |
| Invesco | Workday |

The title rule is implemented in `jobwatcher/title_rules.py`: a posting is marked `in_role=true` when its title matches a finance-track phrase covering commercial and community banking, lending, credit, wealth, financial planning, investments, portfolio work, asset management, risk, treasury, real-estate finance, property management, private banking, trust, client service, affordable-housing finance, program finance, or financial services. Every source is requested as public JSON; no login and no HTML scraping are used.

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

## Repository map

- `.gitignore` — excludes local caches and generated development files.
- `.github/workflows/daily.yml` — runs the source pulls, history build, status update, daily issue, and data commit on a UTC schedule.
- `.github/workflows/pages.yml` — publishes `site/` to GitHub Pages.
- `.github/workflows/tests.yml` — runs pytest on pushes and pull requests.
- `.github/workflows/issue-backfill.yml` — maintenance workflow that restores missing daily issues from committed raw data.
- `pyproject.toml` and `uv.lock` — Python project metadata, dependencies, and locked environment.
- `sources/sources.json` — the 15 employer ATS endpoints and field mappings.
- `data/raw/.gitkeep` — keeps the raw-data directory present before the first run.
- `jobwatcher/__init__.py` — package marker for the Python modules.
- `jobwatcher/history.py` — normalizes source records and rebuilds deterministic history/status files.
- `jobwatcher/title_rules.py` — title-based in-role classification.
- `scripts/run_pipeline.py` — fetches every source, writes compressed raw files, rebuilds data, and invokes issue updates.
- `scripts/build_history.py` — command-line history rebuild from raw files.
- `scripts/update_issue.py` — creates/updates daily issues, closes older ones, and splits large lists into comments.
- `data/raw/<date>/` — compressed JSON source responses and per-source run status.
- `data/history.csv` — canonical one-row-per-posting history.
- `data/status.json` — latest run time, counts, source health, and successful-day count.
- `tests/test_history.py` — common-column, normalization, first-seen, last-seen, removal, and source-history tests.
- `tests/test_title_rules.py` — in-role and unrelated-title tests.
- `site/index.html` — Today page.
- `site/browse.html` — open-role browser, filters, direct application links, and shortlist.
- `site/market.html` — six-section history-driven market report.
- `site/career-fit.html` — exploratory 12-question career-fit quiz.
- `site/app.js` — browser-side data loading, calculations, rendering, filters, charts, shortlist, and quiz logic.
- `site/styles.css` — shared visual system and responsive layout.
- `site/demo-data.js` — clearly labeled fallback seed data for the first local preview.
- `site/data/history.csv` and `site/data/status.json` — deployment copies of the canonical data files.
- `site/manifest.json` — installable web-app metadata and icons.
- `site/icon-192.svg` and `site/icon-512.svg` — Job Watcher app icons.
- `site/sw.js` — offline shell/cache behavior with network-first data loading.
- `README.md` — project overview, source map, commands, and repository documentation.

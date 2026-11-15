"""Fetch every configured ATS source, save raw JSON, and rebuild the site data."""

from __future__ import annotations

import gzip
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

# Keep direct `python scripts/run_pipeline.py` execution working from the
# repository root and from GitHub Actions.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobwatcher.history import _extract_items, build_history

SOURCE_FILE = ROOT / "sources" / "sources.json"


def utc_now() -> datetime:
    return datetime.now(UTC)


def fetch_source(source: dict[str, Any]) -> Any:
    response = requests.get(
        source["endpoint"],
        headers={"User-Agent": "job-watcher/0.1 (+public-course-project)"},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def write_raw(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False)


def main() -> None:
    sources: list[dict[str, Any]] = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    now = utc_now()
    day = now.date().isoformat()
    run_time = now.isoformat().replace("+00:00", "Z")
    raw_dir = ROOT / "data" / "raw" / day
    results: dict[str, dict[str, Any]] = {}

    for source in sources:
        name = source["name"]
        try:
            payload = fetch_source(source)
            raw_path = raw_dir / f"{name}.json.gz"
            write_raw(raw_path, payload)
            count = len(_extract_items(payload, source))
            results[name] = {"ok": True, "count": count}
            print(f"OK   {name}: {count} postings")
        except Exception as error:  # one source must never stop the run
            results[name] = {"ok": False, "count": 0, "error": f"{type(error).__name__}: {error}"}
            print(f"FAIL {name}: {error}")

    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "_run_status.json").write_text(json.dumps({"run_time": run_time, "sources": results}, indent=2) + "\n", encoding="utf-8")
    rows, status = build_history(raw_dir.parent, ROOT / "data" / "history.csv", ROOT / "data" / "status.json", sources=sources, run_time=run_time)
    status["demo"] = False
    (ROOT / "data" / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    (ROOT / "site" / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data" / "history.csv", ROOT / "site" / "data" / "history.csv")
    shutil.copy2(ROOT / "data" / "status.json", ROOT / "site" / "data" / "status.json")
    print(f"Built {len(rows)} history rows; {status['open']} open; {status['days_with_success']} successful dates")

    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_TOKEN"):
        from update_issue import update_issue

        update_issue(rows, status)


if __name__ == "__main__":
    main()

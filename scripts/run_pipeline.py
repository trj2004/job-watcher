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

REQUEST_HEADERS = {
    "User-Agent": "job-watcher/0.2 (+public-course-project)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _request_json(method: str, url: str, **kwargs: Any) -> Any:
    headers = {**REQUEST_HEADERS, **kwargs.pop("headers", {})}
    response = requests.request(method, url, headers=headers, timeout=45, **kwargs)
    response.raise_for_status()
    return response.json()


def _workday_payload(source: dict[str, Any]) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    limit = int(source.get("page_size", 100))
    offset = 0
    max_pages = int(source.get("max_pages", 80))

    for _ in range(max_pages):
        payload = {
            "appliedFacets": source.get("applied_facets", {}),
            "limit": limit,
            "offset": offset,
            "searchText": source.get("search_text", ""),
        }
        headers = {
            "Origin": source["site_base"],
            "Referer": f"{source['site_base']}/{source['site_path'].strip('/')}",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            page = _request_json("POST", source["endpoint"], json=payload, headers=headers)
        except requests.HTTPError as error:
            # Some Workday tenants cap a page at 20 even when a larger limit is
            # accepted by other tenants. Retry the first failed page safely.
            if limit <= 20:
                raise
            limit = 20
            payload["limit"] = limit
            page = _request_json("POST", source["endpoint"], json=payload, headers=headers)

        batch = page.get("jobPostings") or page.get("jobs") or []
        if not isinstance(batch, list) or not batch:
            break
        jobs.extend(item for item in batch if isinstance(item, dict))
        offset += len(batch)
        total = page.get("total") or page.get("totalJobs") or page.get("totalJobsCount")
        if isinstance(total, int) and offset >= total:
            break
        if len(batch) < limit:
            break

    return {"jobs": jobs}


def _oracle_payload(source: dict[str, Any]) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    limit = int(source.get("page_size", 100))
    offset = 0
    max_pages = int(source.get("max_pages", 40))

    for _ in range(max_pages):
        params = {
            "onlyData": "true",
            "expand": "requisitionList.secondaryLocations",
            "finder": f"findReqs;siteNumber={source['site_number']},limit={limit},offset={offset},sortBy=POSTING_DATES_DESC",
        }
        payload = _request_json("GET", source["endpoint"], params=params)
        batch: list[dict[str, Any]] = []
        total = None
        for group in payload.get("items", []):
            if not isinstance(group, dict):
                continue
            total = total or group.get("TotalJobsCount") or group.get("totalJobsCount")
            requisitions = group.get("requisitionList", [])
            if isinstance(requisitions, list):
                batch.extend(item for item in requisitions if isinstance(item, dict))
        if not batch:
            break
        for item in batch:
            item = dict(item)
            if not item.get("url") and item.get("Id"):
                item["url"] = source["url_template"].format(id=item["Id"])
            jobs.append(item)
        offset += len(batch)
        if isinstance(total, int) and offset >= total:
            break
        if len(batch) < limit:
            break

    return {"jobs": jobs}


def _eightfold_payload(source: dict[str, Any]) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    limit = int(source.get("page_size", 100))
    start = 0
    max_pages = int(source.get("max_pages", 40))

    for _ in range(max_pages):
        params = {"domain": source["domain"], "start": start, "limit": limit}
        payload = _request_json("GET", source["endpoint"], params=params)
        batch = payload.get("data", {}).get("positions", [])
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            item = dict(item)
            position_url = item.get("positionUrl")
            if position_url and str(position_url).startswith("/"):
                item["positionUrl"] = f"{source['url_prefix'].rstrip('/')}{position_url}"
            jobs.append(item)
        start += len(batch)
        total = payload.get("data", {}).get("total")
        if isinstance(total, int) and start >= total:
            break
        if len(batch) < limit:
            break

    return {"jobs": jobs}


def fetch_source(source: dict[str, Any]) -> Any:
    ats = str(source.get("ats", "")).lower()
    if ats == "workday":
        return _workday_payload(source)
    if ats == "oracle":
        return _oracle_payload(source)
    if ats == "eightfold":
        return _eightfold_payload(source)
    return _request_json("GET", source["endpoint"])


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

from __future__ import annotations

import gzip
import json
from pathlib import Path

from jobwatcher.history import COMMON_COLUMNS, build_history


def write_raw(root: Path, day: str, source: str, postings: list[dict]) -> None:
    directory = root / day
    directory.mkdir(parents=True, exist_ok=True)
    with gzip.open(directory / f"{source}.json.gz", "wt", encoding="utf-8") as stream:
        json.dump({"jobs": postings}, stream)


def test_history_tracks_first_last_removed_and_reappearance(tmp_path: Path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-01-01", "demo", [{"id": "a", "title": "Commercial Banking Associate", "company": "Demo Bank", "location": "Arkansas", "url": "https://example.com/a"}, {"id": "b", "title": "Marketing Coordinator", "company": "Demo Bank"}])
    write_raw(raw, "2026-01-02", "demo", [{"id": "a", "title": "Commercial Banking Associate", "company": "Demo Bank", "location": "Arkansas", "url": "https://example.com/a"}])
    write_raw(raw, "2026-01-03", "demo", [{"id": "a", "title": "Commercial Banking Associate", "company": "Demo Bank", "location": "Arkansas", "url": "https://example.com/a"}, {"id": "b", "title": "Marketing Coordinator", "company": "Demo Bank"}])

    rows, status = build_history(raw, tmp_path / "history.csv", tmp_path / "status.json", sources=[{"name": "demo"}], run_time="2026-01-03T12:00:00Z")
    by_id = {row["source_id"]: row for row in rows}

    assert list(rows[0]) == COMMON_COLUMNS
    assert by_id["a"]["first_seen"] == "2026-01-01"
    assert by_id["a"]["last_seen"] == "2026-01-03"
    assert by_id["a"]["first_run"] == "true"
    assert by_id["a"]["status"] == "open"
    assert by_id["b"]["first_seen"] == "2026-01-01"
    assert by_id["b"]["removed_date"] == ""
    assert status["days_with_success"] == 3
    assert status["new_today"] == 0


def test_missing_listing_is_removed_only_when_source_has_a_raw_file(tmp_path: Path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-01-01", "demo", [{"id": "a", "title": "Financial Analyst", "company": "Demo"}])
    (raw / "2026-01-02").mkdir(parents=True)
    write_raw(raw, "2026-01-03", "demo", [])
    rows, status = build_history(raw, tmp_path / "history.csv", tmp_path / "status.json", sources=[{"name": "demo"}])

    assert rows[0]["status"] == "removed"
    assert rows[0]["removed_date"] == "2026-01-03"
    assert status["removed_today"] == 1

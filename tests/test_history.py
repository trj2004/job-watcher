from __future__ import annotations

import gzip
import json
from pathlib import Path

from jobwatcher.history import COMMON_COLUMNS, build_history, normalize_posting


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


def test_nested_ats_fields_and_millisecond_dates_are_normalized():
    row = normalize_posting(
        {
            "id": "wealthfront-1",
            "text": "Financial Planning Associate",
            "categories": {"department": "Client Services", "allLocations": ["Dallas, TX", "Remote"]},
            "createdAt": 1763164800000,
            "hostedUrl": "https://example.com/wealthfront-1",
        },
        "Wealthfront",
        {
            "employer": "Wealthfront",
            "fields": {
                "source_id": "id",
                "title": "text",
                "location": "categories.allLocations",
                "department": "categories.department",
                "posted_date": "createdAt",
                "url": "hostedUrl",
            },
        },
    )

    assert row["source_id"] == "wealthfront-1"
    assert row["location"] == "Dallas, TX, Remote"
    assert row["department"] == "Client Services"
    assert row["posted_date"] == "2025-11-15"


def test_relative_url_epoch_date_and_location_parts_are_normalized():
    row = normalize_posting(
        {
            "id": 549800790247,
            "name": "Premier Relationship Manager",
            "primary_city": "Dallas",
            "primary_state": "Texas",
            "postedTs": 1763164800,
            "positionUrl": "/careers/job/549800790247",
        },
        "Morgan Stanley",
        {
            "url_prefix": "https://morganstanley.eightfold.ai",
            "location_fields": ["primary_city", "primary_state"],
            "employer": "Morgan Stanley",
            "fields": {"source_id": "id", "title": "name", "location": "positionUrl", "posted_date": "postedTs", "url": "positionUrl"},
        },
    )

    assert row["location"] == "Dallas, Texas"
    assert row["employer"] == "Morgan Stanley"
    assert row["posted_date"] == "2025-11-15"
    assert row["url"] == "https://morganstanley.eightfold.ai/careers/job/549800790247"


def test_history_ignores_raw_files_from_removed_sources(tmp_path: Path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-01-01", "old-source", [{"id": "old", "title": "Financial Analyst"}])
    write_raw(raw, "2026-01-01", "active-source", [{"id": "active", "title": "Financial Analyst"}])

    rows, _ = build_history(raw, tmp_path / "history.csv", tmp_path / "status.json", sources=[{"name": "active-source"}])

    assert [row["source_id"] for row in rows] == ["active"]

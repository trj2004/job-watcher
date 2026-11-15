"""Deterministic history building from compressed daily raw files."""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .title_rules import in_role

COMMON_COLUMNS = [
    "posting_id",
    "source",
    "source_id",
    "employer",
    "title",
    "location",
    "department",
    "posted_date",
    "url",
    "in_role",
    "first_run",
    "first_seen",
    "last_seen",
    "status",
    "removed_date",
]

FIELD_CANDIDATES = {
    "source_id": ("source_id", "id", "job_id", "jobId", "requisition_id", "requisitionId", "slug"),
    "employer": ("employer", "company", "company_name", "companyName", "organization", "name"),
    "title": ("title", "name", "job_title", "jobTitle", "text"),
    "location": ("location", "location_name", "locationName", "city", "locations"),
    "department": ("department", "department_name", "departmentName", "team", "category"),
    "posted_date": ("posted_date", "postedDate", "created_at", "createdAt", "date_posted", "datePosted"),
    "url": ("url", "absolute_url", "absoluteUrl", "apply_url", "applyUrl", "hostedUrl", "job_url"),
}


def _value(record: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, "", []):
            return record[key]
    return ""


def _path_value(record: Mapping[str, Any], path: str) -> Any:
    """Read a simple dotted path from a nested ATS record."""

    current: Any = record
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return ""
        current = current.get(part, "")
    return current


def _flatten_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "value", "city", "text"):
            if value.get(key):
                return _flatten_value(value[key])
        return ", ".join(_flatten_value(item) for item in value.values() if item)
    if isinstance(value, list):
        return ", ".join(_flatten_value(item) for item in value if item)
    return str(value).strip() if value is not None else ""


def _extract_items(payload: Any, source_config: Mapping[str, Any] | None = None) -> list[Mapping[str, Any]]:
    """Find job records in common ATS response shapes."""

    config = source_config or {}
    current = payload
    path = config.get("items_path", "")
    if path:
        for part in path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part, [])
            else:
                current = []
    if isinstance(current, list):
        return [item for item in current if isinstance(item, Mapping)]
    if isinstance(current, Mapping):
        for key in ("postings", "jobs", "results", "content", "data"):
            if isinstance(current.get(key), list):
                return [item for item in current[key] if isinstance(item, Mapping)]
        if any(key in current for key in FIELD_CANDIDATES["title"]):
            return [current]
    return []


def normalize_posting(raw: Mapping[str, Any], source: str, source_config: Mapping[str, Any] | None = None) -> dict[str, str]:
    """Convert one source record to the common schema before history dates are applied."""

    config = source_config or {}
    mapped = config.get("fields", {})
    values: dict[str, Any] = {}
    for field in ("source_id", "employer", "title", "location", "department", "posted_date", "url"):
        configured = mapped.get(field)
        if isinstance(configured, str):
            values[field] = _path_value(raw, configured)
        elif isinstance(configured, list):
            values[field] = _value(raw, configured)
        else:
            values[field] = _value(raw, FIELD_CANDIDATES[field])

    location_fields = config.get("location_fields")
    if isinstance(location_fields, list):
        values["location"] = [
            value for field in location_fields
            if (value := _path_value(raw, str(field))) not in (None, "", [])
        ]

    source_id = _flatten_value(values["source_id"])
    if not source_id:
        raise ValueError(f"source record has no source ID: {raw!r}")
    employer = (
        str(config["employer"])
        if config.get("employer") and not mapped.get("employer")
        else _flatten_value(values["employer"]) or config.get("employer", source)
    )
    title = _flatten_value(values["title"]) or "Untitled posting"
    url = _flatten_value(values["url"])
    if not url and config.get("url_template"):
        url = str(config["url_template"]).format(source_id=source_id)
    if url.startswith("/") and config.get("url_prefix"):
        url = f"{str(config['url_prefix']).rstrip('/')}{url}"
    posted_value = values["posted_date"]
    if isinstance(posted_value, (int, float)):
        timestamp = posted_value / 1000 if posted_value > 10_000_000_000 else posted_value
        posted_date = datetime.fromtimestamp(timestamp, UTC).date().isoformat()
    else:
        posted_text = _flatten_value(posted_value)
        try:
            posted_date = datetime.fromisoformat(posted_text.replace("Z", "+00:00")).date().isoformat()[:10]
        except ValueError:
            posted_date = posted_text[:10]
    return {
        "posting_id": f"{source}:{source_id}",
        "source": source,
        "source_id": source_id,
        "employer": employer,
        "title": title,
        "location": _flatten_value(values["location"]),
        "department": _flatten_value(values["department"]),
        "posted_date": posted_date,
        "url": url,
        "in_role": "true" if in_role(title) else "false",
    }


def _read_json_gzip(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COMMON_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_run_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_history(
    raw_root: str | Path,
    output_history: str | Path,
    output_status: str | Path,
    sources: list[Mapping[str, Any]] | None = None,
    run_time: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Rebuild history and status from all available daily raw files."""

    root = Path(raw_root)
    source_configs = {str(item["name"]): item for item in (sources or [])}
    files: list[tuple[str, str, Path]] = []
    for day_dir in sorted(path for path in root.glob("????-??-??") if path.is_dir()):
        for raw_path in sorted(day_dir.glob("*.json.gz")):
            source = raw_path.name.removesuffix(".json.gz")
            if source_configs and source not in source_configs:
                continue
            files.append((day_dir.name, source, raw_path))

    source_first_dates: dict[str, str] = {}
    for day, source, _ in files:
        source_first_dates[source] = min(day, source_first_dates.get(source, day))

    records: dict[str, dict[str, str]] = {}
    counts_by_day_source: dict[tuple[str, str], int] = {}
    successful_raw: set[tuple[str, str]] = set()
    for day, source, raw_path in files:
        config = source_configs.get(source, {})
        items = _extract_items(_read_json_gzip(raw_path), config)
        successful_raw.add((day, source))
        seen_ids: set[str] = set()
        for item in items:
            try:
                normalized = normalize_posting(item, source, config)
            except ValueError:
                continue
            posting_id = normalized["posting_id"]
            seen_ids.add(posting_id)
            existing = records.get(posting_id)
            if existing is None:
                records[posting_id] = {
                    **normalized,
                    "first_run": "true" if day == source_first_dates[source] else "false",
                    "first_seen": day,
                    "last_seen": day,
                    "status": "open",
                    "removed_date": "",
                }
            else:
                for field in ("employer", "title", "location", "department", "posted_date", "url", "in_role"):
                    if normalized[field]:
                        existing[field] = normalized[field]
                existing["last_seen"] = day
                existing["status"] = "open"
                existing["removed_date"] = ""
        counts_by_day_source[(day, source)] = len(seen_ids)
        for posting_id, existing in records.items():
            if existing["source"] == source and existing["status"] == "open" and posting_id not in seen_ids:
                existing["status"] = "removed"
                existing["removed_date"] = day

    rows = [records[key] for key in sorted(records)]
    _write_csv(Path(output_history), rows)

    all_days = sorted({day for day, _, _ in files})
    latest_day = all_days[-1] if all_days else ""
    run_status = _read_run_status(root / latest_day / "_run_status.json") if latest_day else {}
    configured_names = list(source_configs) or sorted({source for _, source, _ in files})
    source_status: list[dict[str, Any]] = []
    for source in configured_names:
        result = run_status.get("sources", {}).get(source, {}) if isinstance(run_status.get("sources"), Mapping) else {}
        count = counts_by_day_source.get((latest_day, source), 0)
        source_status.append({"name": source, "ok": bool(result.get("ok", (latest_day, source) in successful_raw)), "count": count})
    status = {
        "run_time": run_time or (run_status.get("run_time") if run_status else datetime.now(UTC).isoformat().replace("+00:00", "Z")),
        "first_run_date": all_days[0] if all_days else "",
        "days_with_success": len(all_days),
        "open": sum(row["status"] == "open" for row in rows),
        "new_today": sum(row["first_seen"] == latest_day and row["first_run"] == "false" for row in rows),
        "removed_today": sum(row["removed_date"] == latest_day for row in rows),
        "sources": source_status,
    }
    Path(output_status).parent.mkdir(parents=True, exist_ok=True)
    Path(output_status).write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return rows, status

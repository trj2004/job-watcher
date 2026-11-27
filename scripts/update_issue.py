"""Create or update the daily GitHub Issue required by the assignment."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobwatcher.history import build_history

SOURCE_FILE = ROOT / "sources" / "sources.json"
MAX_ISSUE_BODY = 60_000
COMMENT_MARKER = "<!-- job-watcher-generated-list -->"


def api_request(method: str, url: str, token: str, payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "User-Agent": "job-watcher"})
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=30) as response:
        content = response.read()
        return json.loads(content.decode("utf-8")) if content else {}


def _row_line(row: dict[str, str]) -> str:
    title = row.get("title", "Untitled posting").replace("\n", " ").strip()
    employer = row.get("employer", "Unknown employer").replace("\n", " ").strip()
    url = row.get("url", "") or "#"
    return f"- [{title} — {employer}]({url})"


def _issue_content(date: str, rows: list[dict[str, str]], status: dict) -> tuple[str, list[str]]:
    new_rows = [row for row in rows if row["first_seen"] == date and row["first_run"] == "false"]
    removed_rows = [row for row in rows if row["removed_date"] == date]
    source_count = sum(item.get("ok", False) for item in status.get("sources", []))
    source_total = len(status.get("sources", []))
    summary = [
        f"## Daily change brief — {date}",
        "",
        f"Sources successful: {source_count}/{source_total}",
        f"New postings: {len(new_rows)}",
        f"Removed postings: {len(removed_rows)}",
    ]
    sections = [
        ("New postings", [_row_line(row) for row in new_rows] or ["- None"]),
        ("Removed postings", [_row_line(row) for row in removed_rows] or ["- None"]),
    ]
    body_lines = summary[:]
    for heading, lines in sections:
        body_lines.extend(["", f"### {heading}", "", *lines])
    body = "\n".join(body_lines)
    if len(body) <= MAX_ISSUE_BODY:
        return body, []

    comments: list[str] = []
    for heading, lines in sections:
        current = [f"### {heading}", ""]
        for line in lines:
            if len("\n".join(current + [line])) > 45_000 and len(current) > 2:
                comments.append("\n".join(current))
                current = [f"### {heading} (continued)", ""]
            current.append(line)
        if len(current) > 2:
            comments.append("\n".join(current))
    summary_body = "\n".join(summary + ["", "The full posting lists are included in the generated comments below."])
    return summary_body, comments


def _sync_issue(api: str, token: str, existing: dict | None, title: str, body: str, comments: list[str]) -> dict:
    if existing:
        number = existing["number"]
        issue = api_request("PATCH", f"{api}/issues/{number}", token, {"body": body})
    else:
        issue = api_request("POST", f"{api}/issues", token, {"title": title, "body": body})
        number = issue["number"]

    old_comments = api_request("GET", f"{api}/issues/{number}/comments?per_page=100", token)
    for comment in old_comments if isinstance(old_comments, list) else []:
        if COMMENT_MARKER in comment.get("body", ""):
            api_request("DELETE", comment["url"], token)
    for index, comment_body in enumerate(comments, start=1):
        api_request(
            "POST",
            f"{api}/issues/{number}/comments",
            token,
            {"body": f"{COMMENT_MARKER}\n\n{comment_body}\n\n_List {index} of {len(comments)}._"},
        )
    return issue


def update_issue(rows: list[dict[str, str]], status: dict) -> None:
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    api = f"https://api.github.com/repos/{repository}"
    date = datetime.fromisoformat(status["run_time"].replace("Z", "+00:00")).astimezone(UTC).date().isoformat()
    title = f"Job Watcher — {date}"
    body, comments = _issue_content(date, rows, status)
    try:
        issues = api_request("GET", f"{api}/issues?state=all&per_page=100", token)
        for issue in issues:
            if issue.get("title", "").startswith("Job Watcher — ") and issue["title"] != title:
                if issue.get("state") == "open":
                    api_request("PATCH", f"{api}/issues/{issue['number']}", token, {"state": "closed"})
        existing = next((issue for issue in issues if issue.get("title") == title), None)
        if existing and existing.get("state") == "closed":
            api_request("PATCH", f"{api}/issues/{existing['number']}", token, {"state": "open"})
        _sync_issue(api, token, existing, title, body, comments)
    except HTTPError as error:
        print(f"Issue update failed: {error}")


def backfill_issues() -> None:
    """Create or refresh one issue for every raw-data date in the repository."""

    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    api = f"https://api.github.com/repos/{repository}"
    sources = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    raw_root = ROOT / "data" / "raw"
    dates = sorted(path.name for path in raw_root.glob("????-??-??") if path.is_dir())
    if not dates:
        print("No raw-data dates found; no issues to backfill")
        return

    try:
        issues = api_request("GET", f"{api}/issues?state=all&per_page=100", token)
        issue_map = {issue.get("title"): issue for issue in issues if issue.get("title", "").startswith("Job Watcher — ")}
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for date in dates:
                rows, status = build_history(raw_root, temp / f"{date}.csv", temp / f"{date}.json", sources=sources, end_date=date)
                title = f"Job Watcher — {date}"
                body, comments = _issue_content(date, rows, status)
                existing = issue_map.get(title)
                if date == dates[-1] and existing and existing.get("state") == "closed":
                    api_request("PATCH", f"{api}/issues/{existing['number']}", token, {"state": "open"})
                issue_map[title] = _sync_issue(api, token, existing, title, body, comments)

        current_title = f"Job Watcher — {dates[-1]}"
        for issue in issue_map.values():
            if issue.get("title", "").startswith("Job Watcher — ") and issue.get("title") != current_title and issue.get("state") == "open":
                api_request("PATCH", f"{api}/issues/{issue['number']}", token, {"state": "closed"})
        print(f"Backfilled {len(dates)} daily issues")
    except HTTPError as error:
        print(f"Issue backfill failed: {error}")


if __name__ == "__main__":
    backfill_issues()

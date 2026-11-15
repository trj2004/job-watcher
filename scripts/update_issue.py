"""Create or update the daily GitHub Issue required by the assignment."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def api_request(method: str, url: str, token: str, payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "User-Agent": "job-watcher"})
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")) if response.readable() else {}


def update_issue(rows: list[dict[str, str]], status: dict) -> None:
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    api = f"https://api.github.com/repos/{repository}"
    date = datetime.fromisoformat(status["run_time"].replace("Z", "+00:00")).astimezone(UTC).date().isoformat()
    title = f"Job Watcher — {date}"
    new_rows = [row for row in rows if row["first_seen"] == date and row["first_run"] == "false"]
    removed_rows = [row for row in rows if row["removed_date"] == date]
    lines = [f"## Daily change brief — {date}", "", f"Sources successful: {sum(item['ok'] for item in status['sources'])}/{len(status['sources'])}", "", "### New postings", ""]
    lines += [f"- [{row['title']} — {row['employer']}]({row['url']})" for row in new_rows] or ["- None"]
    lines += ["", "### Removed postings", ""]
    lines += [f"- [{row['title']} — {row['employer']}]({row['url']})" for row in removed_rows] or ["- None"]
    body = "\n".join(lines)
    try:
        issues = api_request("GET", f"{api}/issues?state=open&per_page=100", token)
        for issue in issues:
            if issue.get("title", "").startswith("Job Watcher — ") and issue["title"] != title:
                api_request("PATCH", f"{api}/issues/{issue['number']}", token, {"state": "closed"})
        existing = next((issue for issue in issues if issue.get("title") == title), None)
        if existing:
            api_request("PATCH", f"{api}/issues/{existing['number']}", token, {"body": body})
        else:
            api_request("POST", f"{api}/issues", token, {"title": title, "body": body})
    except HTTPError as error:
        print(f"Issue update failed: {error}")


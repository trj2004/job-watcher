from __future__ import annotations

import json
import shutil
from pathlib import Path

from jobwatcher.history import build_history


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources" / "sources.json"


def main() -> None:
    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []
    rows, status = build_history(ROOT / "data" / "raw", ROOT / "data" / "history.csv", ROOT / "data" / "status.json", sources=sources)
    (ROOT / "site" / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data" / "history.csv", ROOT / "site" / "data" / "history.csv")
    shutil.copy2(ROOT / "data" / "status.json", ROOT / "site" / "data" / "status.json")
    print(f"built {len(rows)} history rows; {status['open']} open; {status['days_with_success']} successful dates")


if __name__ == "__main__":
    main()

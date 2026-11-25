#!/usr/bin/env python3
"""Exit 0 if jobs-live.json was already generated on today's America/Toronto date; else 1.
Used by the daily workflow so a late GitHub cron still runs, but a second trigger the same day is skipped.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

TORONTO = dt.timezone(dt.timedelta(hours=-5))  # fallback if zoneinfo missing in winter; prefer zoneinfo


def today_toronto() -> dt.date:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Toronto")).date()
    except Exception:
        return dt.datetime.now(dt.timezone.utc).astimezone(TORONTO).date()


def generated_date(path: Path) -> dt.date | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("generated_at") or ""
    try:
        when = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return when.astimezone(ZoneInfo("America/Toronto")).date()
    except Exception:
        return when.astimezone(TORONTO).date()


def main(argv: list[str] | None = None) -> int:
    path = Path(argv[0] if argv else (sys.argv[1] if len(sys.argv) > 1 else "jobs-live.json"))
    got = generated_date(path)
    today = today_toronto()
    if got == today:
        print(f"{path} generated_at date is {got} (already today in America/Toronto).")
        return 0
    print(f"{path} generated_at date is {got}; today in America/Toronto is {today}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

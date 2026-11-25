#!/usr/bin/env python3
"""Append one Daily Find to posts.json and validate the file.

Example:
  python3 scripts/add-post.py \\
    --id p-2026-11-26-example \\
    --date 2026-11-26 \\
    --track OHS \\
    --type job \\
    --title "Health and Safety Coordinator (Ottawa)" \\
    --org "Example Builders" \\
    --summary "Entry-level safety coordinator role in Ottawa. An OHS diploma is an asset." \\
    --url "https://example.com/jobs/123" \\
    --status open

  python3 scripts/add-post.py --validate-only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "posts.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TRACKS = {"OHS", "CM", "Both"}
TYPES = {"job", "free_training", "volunteer"}
STATUSES = {"open", "closed"}
REQUIRED = ("id", "date", "track", "type", "title", "org", "summary", "url", "status")


def load() -> dict:
    data = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("posts"), list):
        raise SystemExit(f"{POSTS_PATH} must be an object with a posts array")
    if "schema" not in data:
        data["schema"] = 1
    if "job_max_age_days" not in data:
        data["job_max_age_days"] = 30
    return data


def valid_date(value: str, field: str) -> None:
    if not DATE_RE.match(value):
        raise SystemExit(f"{field} must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"{field} is not a real date: {value}") from exc


def validate_post(post: dict, seen_ids: set[str] | None = None) -> None:
    if not isinstance(post, dict):
        raise SystemExit("each post must be an object")
    for key in REQUIRED:
        if key not in post or post[key] in (None,):
            raise SystemExit(f"missing {key}")
        if key != "url" and isinstance(post[key], str) and not str(post[key]).strip():
            raise SystemExit(f"{key} must not be empty")
    if not ID_RE.match(str(post["id"])):
        raise SystemExit(f"invalid id: {post['id']}")
    if seen_ids is not None:
        if post["id"] in seen_ids:
            raise SystemExit(f"duplicate id: {post['id']}")
        seen_ids.add(post["id"])
    valid_date(str(post["date"]), "date")
    if post["track"] not in TRACKS:
        raise SystemExit(f"track must be one of {sorted(TRACKS)}")
    if post["type"] not in TYPES:
        raise SystemExit(f"type must be one of {sorted(TYPES)}")
    if post["status"] not in STATUSES:
        raise SystemExit(f"status must be one of {sorted(STATUSES)}")
    url = str(post["url"])
    if not url.startswith(("https://", "http://")):
        raise SystemExit("url must start with https:// or http://")
    end = post.get("end_date") or ""
    if end:
        valid_date(str(end), "end_date")
    rid = post.get("resource_id") or ""
    if rid and not re.match(r"^[a-z]\d{3,}$", str(rid)):
        raise SystemExit(f"invalid resource_id: {rid}")


def validate_file(data: dict) -> int:
    seen: set[str] = set()
    for post in data["posts"]:
        validate_post(post, seen)
    return len(data["posts"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--id")
    p.add_argument("--date")
    p.add_argument("--track", choices=sorted(TRACKS))
    p.add_argument("--type", choices=sorted(TYPES))
    p.add_argument("--title")
    p.add_argument("--org")
    p.add_argument("--summary")
    p.add_argument("--url")
    p.add_argument("--end-date", default="", dest="end_date")
    p.add_argument("--status", default="open", choices=sorted(STATUSES))
    p.add_argument("--resource-id", default="", dest="resource_id")
    p.add_argument("--validate-only", action="store_true", help="check posts.json and exit")
    p.add_argument("--dry-run", action="store_true", help="validate the new post without writing")
    args = p.parse_args()

    data = load()
    if args.validate_only:
        n = validate_file(data)
        print(f"OK: {n} posts in {POSTS_PATH}")
        return 0

    needed = ("id", "date", "track", "type", "title", "org", "summary", "url")
    missing = [k for k in needed if not getattr(args, k)]
    if missing:
        p.error("the following arguments are required: " + ", ".join("--" + k.replace("_", "-") for k in missing))

    post = {
        "id": args.id,
        "date": args.date,
        "track": args.track,
        "type": args.type,
        "title": args.title,
        "org": args.org,
        "summary": args.summary,
        "url": args.url,
        "end_date": args.end_date or "",
        "status": args.status,
    }
    if args.resource_id:
        post["resource_id"] = args.resource_id

    seen = {x["id"] for x in data["posts"] if isinstance(x, dict) and "id" in x}
    validate_post(post, seen)
    validate_file(data)
    data["posts"].append(post)
    if args.dry_run:
        print(json.dumps(post, indent=2, ensure_ascii=False))
        print("Dry run: posts.json not changed")
        return 0
    POSTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Appended {post['id']} ({len(data['posts'])} posts). Next:")
    print(f'  git add posts.json && git commit -m "Add Daily Find: {post["title"]}" && git push origin main')
    return 0


if __name__ == "__main__":
    sys.exit(main())

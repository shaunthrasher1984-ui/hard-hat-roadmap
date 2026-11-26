#!/usr/bin/env python3
"""Check every HTTP(S) link in guides.json (and the resume template path).
Writes guides-link-check.json and, when present, adds a 'links' block to weekly-update.json.
Does not fail the weekly job solely because an external page is down — it flags broken URLs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import ssl
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
UA = "HardHatRoadmapLinkCheck/1.0 (+https://shaunthrasher1984-ui.github.io/hard-hat-roadmap/)"
CTX = ssl.create_default_context()


def walk(obj, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"url", "wages_url", "outlook_url", "requirements_url", "act_url", "guide_url"} and isinstance(v, str) and v.startswith("http"):
                out.add(v)
            else:
                walk(v, out)
    elif isinstance(obj, list):
        for x in obj:
            walk(x, out)
    elif isinstance(obj, str) and obj.startswith("http"):
        out.add(obj)


def check(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return {"url": url, "status": r.status, "final": r.geturl(), "ok": r.status in (200, 203)}
    except HTTPError as e:
        return {"url": url, "status": e.code, "final": url, "ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"url": url, "status": 0, "final": url, "ok": False, "error": f"{type(e).__name__}: {e}"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guides", default=str(ROOT / "guides.json"))
    ap.add_argument("--out", default=str(ROOT / "guides-link-check.json"))
    ap.add_argument("--weekly", default=str(ROOT / "weekly-update.json"))
    a = ap.parse_args(argv)
    data = json.loads(Path(a.guides).read_text(encoding="utf-8"))
    urls: set[str] = set()
    walk(data, urls)
    results = [check(u) for u in sorted(urls)]
    broken = [r for r in results if not r["ok"]]
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    report = {
        "schema": 1,
        "checked": now.date().isoformat(),
        "checked_at": now.isoformat().replace("+00:00", "Z"),
        "total": len(results),
        "ok": len(results) - len(broken),
        "broken": broken,
        "results": results,
    }
    Path(a.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    weekly_path = Path(a.weekly)
    if weekly_path.is_file():
        weekly = json.loads(weekly_path.read_text(encoding="utf-8"))
        weekly["links"] = {
            "checked": report["checked"],
            "total": report["total"],
            "ok": report["ok"],
            "broken_count": len(broken),
            "broken": [{"url": b["url"], "status": b.get("status"), "error": b.get("error")} for b in broken],
        }
        weekly_path.write_text(json.dumps(weekly, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Updated {weekly_path} links block")
    print(json.dumps({"out": a.out, "total": report["total"], "ok": report["ok"], "broken": len(broken)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

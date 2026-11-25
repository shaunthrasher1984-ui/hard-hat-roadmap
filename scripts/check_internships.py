#!/usr/bin/env python3
"""Re-check every internships.json posting URL and mark closed or not_found when the live posting is gone.
Does not invent pay or change a status when the check is inconclusive (timeout, 403, network error).
Usage: python3 scripts/check_internships.py [internships.json]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UA = "HardHatRoadmapJobs/1.0 (+https://shaunthrasher1984-ui.github.io/hard-hat-roadmap/; weekly, low volume)"
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()

CLOSED_PHRASES = (
    "no longer available",
    "this job has expired",
    "this job has been expired",
    "job has expired",
    "position has been filled",
    "this requisition is closed",
    "this job is closed",
    "this job has been closed",
    "job is no longer",
    "no longer accepting applications",
    "no longer accepting candidates",
    "this posting has been filled",
    "this posting is closed",
    "cette offre n'est plus",
    "cette offre n’est plus",
    "n'est plus disponible",
    "n’est plus disponible",
    "poste comblé",
    "poste comble",
    "offre expirée",
    "offre expiree",
    "no longer accepting",
)

# Pages that are clearly a careers index rather than the posting itself
CAREERS_HINTS = (
    "view all jobs",
    "search jobs",
    "all open positions",
    "no jobs found",
    "job not found",
    "page not found",
)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        t = re.sub(r"\s+", " ", data).strip()
        if not t:
            return
        if self._in_title:
            self.title += " " + t
        self.parts.append(t)


def visible_text(html: bytes) -> tuple[str, str]:
    parser = _Text()
    try:
        parser.feed(html.decode("utf-8", errors="replace"))
    except Exception:
        raw = html.decode("utf-8", errors="replace")
        return "", raw.lower()
    title = re.sub(r"\s+", " ", parser.title).strip()
    return title, " ".join(parser.parts).lower()


def fetch(url: str, timeout: int = 25) -> tuple[int | None, str, bytes]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.getcode(), r.geturl(), r.read(800_000)
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(200_000)
        except Exception:
            pass
        return e.code, e.geturl() if hasattr(e, "geturl") else url, body
    except Exception as e:
        return None, str(e), b""


def classify(status: int | None, final_url: str, title: str, text: str) -> str | None:
    """Return live, closed, not_found, or None if inconclusive."""
    if status is None:
        return None
    if status in (404, 410, 451):
        return "not_found"
    if status in (401, 403, 429) or status >= 500:
        return None
    if status != 200:
        return None
    blob = f"{title.lower()} {text}"
    if any(p in blob for p in CLOSED_PHRASES):
        return "closed"
    # A 200 careers homepage after a redirect away from a job path is treated as not found
    path = final_url.lower()
    if any(p in blob for p in ("page not found", "job not found", "this job was not found")):
        return "not_found"
    return "live"


def check_one(posting: dict) -> dict:
    url = (posting.get("link") or "").strip()
    result = dict(posting)
    if not url:
        result["status"] = "not_found"
        result["checked"] = TODAY
        return result
    code, final, body = fetch(url)
    title, text = visible_text(body) if body else ("", "")
    verdict = classify(code, final if isinstance(final, str) else "", title, text)
    if verdict is None:
        result["check_note"] = f"Inconclusive on {TODAY} (HTTP {code if code is not None else 'error'})."
        return result
    result["status"] = verdict
    result["checked"] = TODAY
    result.pop("check_note", None)
    if verdict == "not_found" and result.get("careers"):
        # Keep a usable link: the employer careers page
        result["link"] = result["careers"]
        if result.get("note"):
            if "Posting not found" not in result["note"]:
                result["note"] = "Posting not found – check employer careers page. " + result["note"]
        else:
            result["note"] = "Posting not found – check employer careers page."
    return result


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0] if args else ROOT / "internships.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    postings = data.get("postings") or []
    updated = []
    counts = {"live": 0, "closed": 0, "not_found": 0, "inconclusive": 0, "changed": 0}
    for p in postings:
        before = p.get("status")
        q = check_one(p)
        after = q.get("status")
        if after in counts:
            counts[after] += 1
        else:
            counts["inconclusive"] += 1
        if after != before and q.get("checked") == TODAY:
            counts["changed"] += 1
            print(f"  {p.get('id')}: {before} -> {after}")
        else:
            print(f"  {p.get('id')}: {after or before} (HTTP check)")
        updated.append(q)
    data["postings"] = updated
    data["checked"] = TODAY
    data["updated"] = TODAY
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    print(json.dumps({"file": str(path), "checked": TODAY, **counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

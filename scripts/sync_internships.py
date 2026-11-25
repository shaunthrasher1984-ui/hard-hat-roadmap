#!/usr/bin/env python3
"""Copy internships.json into the <script id="internships-data"> tag in index.html."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "internships.json"
HTML_PATH = ROOT / "index.html"
START = '<script type="application/json" id="internships-data">'
END = "</script>"


def main() -> int:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    html = HTML_PATH.read_text(encoding="utf-8")
    pat = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.S,
    )
    block = START + "\n" + payload + "\n" + END
    if not pat.search(html):
        sys.stderr.write("Could not find <script id=\"internships-data\"> in index.html\n")
        return 1
    HTML_PATH.write_text(pat.sub(block, html, count=1), encoding="utf-8")
    print(f"Synced {len(data.get('postings', []))} postings into index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

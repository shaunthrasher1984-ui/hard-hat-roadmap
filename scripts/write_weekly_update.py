#!/usr/bin/env python3
"""Compare previous vs current jobs and internships; write weekly-update.json and sync it into index.html.
Usage:
  python3 scripts/write_weekly_update.py \\
    --baseline /tmp/prev-weekly-update.json \\
    --prev-jobs /tmp/prev-jobs-live.json --jobs jobs-live.json \\
    --prev-internships /tmp/prev-internships.json --internships internships.json \\
    --out weekly-update.json

Job "new" / "dropped" counts are week-over-week: they prefer job ids saved in the
previous weekly-update.json (--baseline) so a mid-week daily jobs-live refresh
does not zero out Monday's "what changed this week" note.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
START = '<script type="application/json" id="weekly-update-data">'
END = "</script>"


def load(path: Path | None) -> dict:
    if not path or not Path(path).is_file():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def job_ids(data: dict) -> set[str]:
    return {str(j.get("id")) for j in (data.get("jobs") or []) if j.get("id")}


def iso_date(s: str) -> str:
    return (s or "")[:10]


def build(prev_jobs: dict, jobs: dict, prev_in: dict, internships: dict, baseline: dict | None = None) -> dict:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    today = now.date().isoformat()
    new_ids = job_ids(jobs)
    baseline = baseline or {}
    base_ids = baseline.get("jobs") or {}
    if isinstance(base_ids.get("ids"), list) and base_ids.get("ids"):
        old_ids = {str(i) for i in base_ids["ids"] if i}
    else:
        old_ids = job_ids(prev_jobs)
    added = sorted(new_ids - old_ids)
    dropped = sorted(old_ids - new_ids)
    counts = jobs.get("counts") or {}
    # internships
    prev_map = {p.get("id"): p for p in (prev_in.get("postings") or [])}
    cur = internships.get("postings") or []
    newly_closed, newly_missing, still_live = [], [], 0
    for p in cur:
        pid, st = p.get("id"), p.get("status")
        before = (prev_map.get(pid) or {}).get("status")
        if st == "live":
            still_live += 1
        if st == "closed" and before != "closed":
            newly_closed.append({"id": pid, "employer": p.get("employer"), "title": p.get("title")})
        if st == "not_found" and before != "not_found":
            newly_missing.append({"id": pid, "employer": p.get("employer"), "title": p.get("title")})
    summary = {
        "en": _summary_en(len(new_ids), counts, len(added), len(dropped), still_live, len(newly_closed), len(newly_missing)),
        "fr": _summary_fr(len(new_ids), counts, len(added), len(dropped), still_live, len(newly_closed), len(newly_missing)),
        "es": _summary_es(len(new_ids), counts, len(added), len(dropped), still_live, len(newly_closed), len(newly_missing)),
    }
    return {
        "schema": 1,
        "updated": today,
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "jobs": {
            "generated_at": jobs.get("generated_at"),
            "count": len(new_ids),
            "ohs": int(counts.get("OHS") or 0),
            "cm": int(counts.get("CM") or 0),
            "new": len(added),
            "dropped": len(dropped),
            "ids": sorted(new_ids),
        },
        "internships": {
            "checked": internships.get("checked") or today,
            "live": still_live,
            "closed": sum(1 for p in cur if p.get("status") == "closed"),
            "not_found": sum(1 for p in cur if p.get("status") == "not_found"),
            "newly_closed": len(newly_closed),
            "newly_missing": len(newly_missing),
            "changes": newly_closed + newly_missing,
        },
        "summary": summary,
    }


def _summary_en(n, counts, added, dropped, live, closed, missing):
    parts = [
        f"{n} live job postings ({int(counts.get('OHS') or 0)} OHS, {int(counts.get('CM') or 0)} construction management)."
    ]
    if added or dropped:
        bits = []
        if added:
            bits.append(f"{added} new")
        if dropped:
            bits.append(f"{dropped} no longer in the list")
        parts.append("This week: " + ", ".join(bits) + ".")
    else:
        parts.append("No change in the live jobs list since the last refresh.")
    intern = f"{live} internship or student role{'s' if live != 1 else ''} still open."
    if closed or missing:
        extra = []
        if closed:
            extra.append(f"{closed} marked closed")
        if missing:
            extra.append(f"{missing} not found")
        intern += " " + ", ".join(extra) + " this week."
    parts.append(intern)
    return " ".join(parts)


def _summary_fr(n, counts, added, dropped, live, closed, missing):
    parts = [
        f"{n} offres d’emploi en direct ({int(counts.get('OHS') or 0)} SST, {int(counts.get('CM') or 0)} gestion de construction)."
    ]
    if added or dropped:
        bits = []
        if added:
            bits.append(f"{added} nouvelle{'s' if added != 1 else ''}")
        if dropped:
            bits.append(f"{dropped} retirée{'s' if dropped != 1 else ''} de la liste")
        parts.append("Cette semaine : " + ", ".join(bits) + ".")
    else:
        parts.append("Aucun changement dans la liste des offres depuis le dernier rafraîchissement.")
    intern = f"{live} stage{'s' if live != 1 else ''} ou poste{'s' if live != 1 else ''} étudiant encore ouvert{'s' if live != 1 else ''}."
    if closed or missing:
        extra = []
        if closed:
            extra.append(f"{closed} marqué{'s' if closed != 1 else ''} fermé{'s' if closed != 1 else ''}")
        if missing:
            extra.append(f"{missing} introuvable{'s' if missing != 1 else ''}")
        intern += " " + ", ".join(extra) + " cette semaine."
    parts.append(intern)
    return " ".join(parts)


def _summary_es(n, counts, added, dropped, live, closed, missing):
    parts = [
        f"{n} ofertas de empleo en vivo ({int(counts.get('OHS') or 0)} SST, {int(counts.get('CM') or 0)} gestión de construcción)."
    ]
    if added or dropped:
        bits = []
        if added:
            bits.append(f"{added} nueva{'s' if added != 1 else ''}")
        if dropped:
            bits.append(f"{dropped} ya no están en la lista")
        parts.append("Esta semana: " + ", ".join(bits) + ".")
    else:
        parts.append("Sin cambios en la lista de ofertas desde la última actualización.")
    intern = f"{live} práctica{'s' if live != 1 else ''} o puesto{'s' if live != 1 else ''} para estudiantes aún abiert{'os' if live != 1 else 'o'}."
    if closed or missing:
        extra = []
        if closed:
            extra.append(f"{closed} marcada{'s' if closed != 1 else ''} como cerrada{'s' if closed != 1 else ''}")
        if missing:
            extra.append(f"{missing} no encontrada{'s' if missing != 1 else ''}")
        intern += " " + ", ".join(extra) + " esta semana."
    parts.append(intern)
    return " ".join(parts)



def _fmt_long(s: str) -> str:
    parts = (s or "")[:10].split("-")
    if len(parts) != 3:
        return s or ""
    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    try:
        return f"{months[int(parts[1])-1]} {int(parts[2])}, {parts[0]}"
    except Exception:
        return s

def _xml(s: str) -> str:
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

def sync_index(data: dict, html_path: Path) -> None:
    if not html_path.is_file():
        return
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    html = html_path.read_text(encoding="utf-8")
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    block = START + "\n" + payload + "\n" + END
    if pat.search(html):
        html = pat.sub(block, html, count=1)
    else:
        print(f"WARNING: {START} not found in {html_path}", file=sys.stderr)
    # Prerender visible note (no layout flash before JS runs)
    summary = (data.get("summary") or {}).get("en") or ""
    when = _fmt_long(data.get("updated") or "")
    if summary:
        html = re.sub(
            r'(<p class="weeksum" data-week-sum>)(.*?)(</p>)',
            lambda m: m.group(1) + _xml(summary) + m.group(3),
            html,
            flags=re.S,
        )
    if when:
        html = re.sub(
            r'(<span data-week-date>)(.*?)(</span>)',
            lambda m: m.group(1) + "· " + when + m.group(3),
            html,
            flags=re.S,
        )
    html_path.write_text(html, encoding="utf-8")
    print(f"Synced weekly-update.json into {html_path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev-jobs")
    ap.add_argument("--jobs", default=str(ROOT / "jobs-live.json"))
    ap.add_argument("--prev-internships")
    ap.add_argument("--internships", default=str(ROOT / "internships.json"))
    ap.add_argument("--out", default=str(ROOT / "weekly-update.json"))
    ap.add_argument("--index", default=str(ROOT / "index.html"))
    ap.add_argument("--baseline", help="Previous weekly-update.json (week-over-week job ids)")
    a = ap.parse_args(argv)
    data = build(load(a.prev_jobs), load(a.jobs), load(a.prev_internships), load(a.internships), load(a.baseline))
    out = Path(a.out)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "updated": data["updated"], "jobs": data["jobs"], "internships": {k: v for k, v in data["internships"].items() if k != "changes"}}, ensure_ascii=False))
    sync_index(data, Path(a.index))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

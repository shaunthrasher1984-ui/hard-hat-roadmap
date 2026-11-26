#!/usr/bin/env python3
"""Inject the seven Guides pages into index.html (idempotent)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
GUIDES = ROOT / "guides.json"

CSS = """
/* ===== Guides (HHRG) ===== */
.ghome{margin:22px 0 8px}
.ghome .ghead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 0 12px}
.ggrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.gcard{display:flex;flex-direction:column;gap:8px;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 16px 14px;box-shadow:var(--shadow);border-top:4px solid var(--teal);min-width:0}
.gcard:hover{border-color:var(--teal)}
.gcard h3{margin:0;font-size:1.02rem;line-height:1.3}
.gcard p{margin:0;color:var(--muted);font-size:.92rem}
.gcard .go{margin-top:auto;font-weight:650;color:var(--teal);font-size:.88rem}
.gtabs{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}
.gtabs a{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:var(--soft);color:var(--ink);text-decoration:none;font-size:.9rem;min-height:40px}
.gtabs a[aria-current=page],.gtabs a:focus-visible{background:var(--tealbg);border-color:var(--teal);font-weight:650}
.gpane{display:none}
.gpane.on,[data-pane=hub] #g-hub,[data-pane=certs] #g-certs,[data-pane=rights] #g-rights,[data-pane=pay] #g-pay,[data-pane=kit] #g-kit,[data-pane=newcomers] #g-newcomers,[data-pane=toolbox] #g-toolbox,[data-pane=designations] #g-designations{display:block}
.gbadge{display:inline-block;font-size:.75rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:999px;background:var(--freebg);color:var(--free)}
.gbadge.fee{background:var(--trialbg);color:var(--trial)}
.gbadge.mix{background:var(--mixbg);color:var(--mix)}
.gbadge.first{background:var(--reqbg);color:var(--req)}
.rightscard{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:18px 20px;box-shadow:var(--shadow)}
.rightscard h3{margin:0 0 8px}
.rightscard ol,.rightscard ul{margin:8px 0 0;padding-left:1.2em}
.talk{margin:0 0 16px}
.talk summary{cursor:pointer;font-weight:700;padding:12px 4px;min-height:44px}
.tmpl{white-space:pre-wrap;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.86rem;line-height:1.45;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:14px;overflow:auto;max-height:28rem}
.gloss{width:100%;border-collapse:collapse}
.gloss th,.gloss td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.gloss th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
@media print{.gtabs,.mainnav,.bottomnav,.ghome,header,nav{display:none!important}#g-rights,.rightscard{display:block!important}}
"""

def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def links(items) -> str:
    if not items:
        return ""
    bits = []
    for it in items:
        if it.get("href"):
            bits.append(f'<a data-nav="{esc(it["href"].split("/")[-1] if it["href"].startswith("#/") else "")}" href="{esc(it["href"])}">{esc(it["label"])}</a>' if False else f'<a href="{esc(it["href"])}">{esc(it["label"])}</a>')
        else:
            bits.append(f'<a href="{esc(it["url"])}" target="_blank" rel="noopener">{esc(it["label"])}</a>')
    return '<p class="cites">' + " · ".join(bits) + "</p>"

def pills():
    items = [
        ("", "Overview"),
        ("certs", "Certification finder"),
        ("rights", "Know your rights"),
        ("pay", "Pay checker"),
        ("kit", "Resume & interview"),
        ("newcomers", "Newcomer corner"),
        ("toolbox", "Toolbox talks"),
        ("designations", "Designations"),
    ]
    out = ['<nav class="gtabs noprint" aria-label="Guides">']
    for sub, label in items:
        href = "#/ohs/guides" + (f"/{sub}" if sub else "")
        out.append(f'<a href="{href}" data-guide="{sub or "hub"}">{esc(label)}</a>')
    out.append("</nav>")
    return "".join(out)

def build_html(d: dict, interview: dict, template: str) -> str:
    cards = [
        ("certs", "Free certification finder", "Ontario tickets employers ask for first, with official cost and validity only where sources state them."),
        ("rights", "Know your rights", "The right to know, participate and refuse unsafe work under the Ontario OHSA, plus what to do if you are hurt."),
        ("pay", "Pay checker", "Real Job Bank wage ranges and outlooks for safety and construction roles — no invented numbers."),
        ("kit", "Resume and interview kit", "A copyable safety resume template, common questions, and STAR sample answers that are clearly fictional."),
        ("newcomers", "Newcomer corner", "Official credential-recognition and settlement links, plus an English, French and Spanish safety glossary."),
        ("toolbox", "Toolbox talk library", "Short original talks on common site hazards, each with a CCOHS or IHSA fact-sheet link."),
        ("designations", "Designation roadmap", "NCSO, CRST, CRSP, Gold Seal and CHSC — official requirements, with uncertainty flagged."),
    ]
    hub_cards = []
    for sub, title, blurb in cards:
        hub_cards.append(
            f'<a class="gcard" href="#/ohs/guides/{sub}" data-guide="{sub}"><span class="gbadge">Free</span><h3>{esc(title)}</h3><p>{esc(blurb)}</p><span class="go">Open this guide</span></a>'
        )

    # certs
    cert_cards = []
    for it in d["certs"]["items"]:
        badges = []
        if it.get("ask_first"):
            badges.append('<span class="gbadge first">Often asked first</span>')
        cost = it.get("cost") or ""
        cls = "fee" if cost.lower().startswith("fee") else ("mix" if "mixed" in cost.lower() or "may charge" in cost.lower() else "")
        badges.append(f'<span class="gbadge {cls}">{esc(cost)}</span>')
        cert_cards.append(
            f'<article class="card" data-cert="{esc(it["id"])}" data-ask="{1 if it.get("ask_first") else 0}">'
            f'<div class="badges">{"".join(badges)}</div>'
            f'<h3>{esc(it["title"])}</h3>'
            f'<p>{esc(it["who"])}</p>'
            f'<dl class="facts"><div><dt>Cost</dt><dd>{esc(it["cost"])}<br>{esc(it.get("cost_note") or "")}</dd></div>'
            f'<div><dt>Validity</dt><dd>{esc(it["validity"])}</dd></div></dl>'
            + links(it.get("links"))
            + "</article>"
        )

    # rights
    rights_blocks = []
    for r in d["rights"]["rights"]:
        cites = "".join(f"<li>{esc(c)}</li>" for c in r["cites"])
        rights_blocks.append(
            f'<article class="rightscard" style="margin-bottom:16px"><h3>{esc(r["title"])}</h3>'
            f'<p>{esc(r["summary"])}</p><ul>{cites}</ul>{links(r.get("links"))}</article>'
        )
    inj = d["rights"]["injured"]
    steps = "".join(f"<li>{esc(s)}</li>" for s in inj["steps"])
    contacts = "".join(f"<li><strong>{esc(c['name'])}.</strong> {esc(c['detail'])}</li>" for c in inj["contacts"])
    injured_html = (
        f'<article class="rightscard"><h3>{esc(inj["title"])}</h3><ol>{steps}</ol>'
        f'<h3 style="margin-top:16px">Contacts</h3><ul>{contacts}</ul>{links(inj.get("links"))}</article>'
    )

    # pay
    pay_cards = []
    for r in d["pay"]["roles"]:
        wage = f'<b>{esc(r["median"])}</b><br>range {esc(r["range"])}' if r.get("median") else "No Job Bank wage is listed for this role on the pages reused from Jobs you could get."
        outl = f'<b>{esc(r["outlook"])}</b><br>{esc(r.get("outlook_period") or "")}' if r.get("outlook") else "Not listed"
        official = []
        if r.get("wages_url"):
            official.append(f'<a href="{esc(r["wages_url"])}" target="_blank" rel="noopener">wages</a>')
        if r.get("outlook_url"):
            official.append(f'<a href="{esc(r["outlook_url"])}" target="_blank" rel="noopener">outlook</a>')
        if r.get("requirements_url"):
            official.append(f'<a href="{esc(r["requirements_url"])}" target="_blank" rel="noopener">requirements</a>')
        noc = f'NOC {esc(r["noc"])}' if r.get("noc") else "No NOC listed"
        pay_cards.append(
            f'<article class="card crole" data-track="{esc(r["track"])}">'
            f'<div class="badges"><span class="b b-soft">{noc}</span><span class="b b-soft">{esc(r["track"])}</span></div>'
            f'<h3>{esc(r["title"])}</h3>'
            f'<dl class="facts"><div><dt>Ontario wage (median)</dt><dd>{wage}</dd></div>'
            f'<div><dt>Outlook, Ontario</dt><dd>{outl}</dd></div></dl>'
            f'<p class="desc">{esc(r.get("requirements_blurb") or "")}</p>'
            f'<p class="cites">{esc(r.get("source_note") or "")} {" · ".join(official)}</p></article>'
        )

    # kit questions
    qs = []
    for bucket, label in (("Both", "All job seekers"), ("OHS", "OHS"), ("CM", "Construction management")):
        for q in interview.get(bucket) or []:
            qs.append(
                f'<article class="card" data-iv="{esc(bucket)}"><div class="badges"><span class="b b-soft">{esc(label)}</span>'
                f'<span class="b b-soft">{esc(q.get("kind") or "")}</span></div>'
                f'<h3>{esc(q.get("q") or "")}</h3>'
                f'<p><strong>What they are often listening for.</strong> {esc(q.get("look") or "")}</p></article>'
            )
    star = d["kit"]["star"]
    star_steps = "".join(
        f'<div class="card"><h3>{esc(s["letter"])} · {esc(s["name"])}</h3><p>{esc(s["text"])}</p></div>' for s in star["steps"]
    )
    examples = "".join(
        f'<article class="panel talk"><h3>{esc(ex["question"])}</h3><p class="note">{esc(ex["label"])}</p>'
        f'<p>{esc(ex["answer"])}</p></article>' for ex in star["examples"]
    )

    # newcomers glossary
    rows = "".join(
        f'<tr><th scope="row">{esc(g["en"])}</th><td lang="fr">{esc(g["fr"])}</td><td lang="es">{esc(g["es"])}</td></tr>'
        for g in d["newcomers"]["glossary"]
    )
    new_secs = []
    for s in d["newcomers"]["sections"]:
        contacts = "".join(f'<p class="note">{esc(c)}</p>' for c in s.get("contacts") or [])
        new_secs.append(f'<article class="panel"><h3>{esc(s["title"])}</h3><p>{esc(s["text"])}</p>{contacts}{links(s.get("links"))}</article>')

    talks = []
    for t in d["toolbox"]["talks"]:
        ask = "".join(f"<li>{esc(a)}</li>" for a in t["ask"])
        talks.append(
            f'<details class="talk panel"><summary>{esc(t["title"])} <span class="b b-soft">{esc(t["minutes"])} min</span></summary>'
            f'<p><strong>Open with:</strong> {esc(t["opening"])}</p>'
            f'<p>{esc(t["talk"])}</p>'
            f'<p><strong>Ask the crew</strong></p><ul>{ask}</ul>{links(t.get("links"))}</details>'
        )

    des = []
    for it in d["designations"]["items"]:
        des.append(
            f'<article class="card" data-track="{esc(it["track"])}">'
            f'<div class="badges"><span class="b b-soft">{esc(it["short"])}</span><span class="b b-soft">{esc(it["org"])}</span>'
            f'<span class="b b-soft">{esc(it["track"])}</span></div>'
            f'<h3>{esc(it["title"])}</h3>'
            f'<p><strong>Requirements (official sources).</strong> {esc(it["requirements"])}</p>'
            f'<p><strong>Timeline.</strong> {esc(it["timeline"])}</p>'
            f'<p class="note">{esc(it.get("uncertainty") or "")}</p>'
            + links(it.get("official"))
            + "</article>"
        )

    html = f'''
<section class="view" id="v-guides" aria-labelledby="h-guides"><div class="wrap">
 <div class="vhead"><span class="kicker" data-i18n="guides_kicker">Guides · free</span>
 <h2 id="h-guides" tabindex="-1" data-i18n="guides_title">Workplace and career guides</h2>
 <p class="lead" data-i18n="guides_lead">Free tools for Ontario safety and construction-management job seekers: certificates, rights, wages, a resume kit, newcomer supports, toolbox talks and designation roadmaps. Official sources were checked on 25 November 2026. This is not legal advice and is not affiliated with the awarding bodies.</p></div>
 {pills()}
 <div class="gpane" id="g-hub">
  <p class="note">{esc(d.get("access_note") or "")} <a href="#/ohs/careers">Jobs you could get</a> and <a href="#/ohs/training">Free training</a> stay just as they were. <a href="#/ohs/skills">Test Your Skills</a> is the practice set for designations.</p>
  <div class="ggrid">{''.join(hub_cards)}</div>
 </div>
 <div class="gpane" id="g-certs">
  <div class="vhead"><h3>Free certification finder</h3><p>{esc(d["certs"]["intro"])}</p></div>
  <p class="note"><strong>What employers ask for first.</strong> {esc(d["certs"]["employers_first"])}</p>
  <div class="filters noprint"><label class="search"><span class="sr">Search certificates</span><input id="gCertQ" type="search" placeholder="Search (e.g. WHMIS, heights)" autocomplete="off"></label>
  <div class="chips" id="gCertFilt" role="group" aria-label="Filter certificates"><button type="button" class="chip" data-cf="all" aria-pressed="true">All</button><button type="button" class="chip" data-cf="first" aria-pressed="false">Asked first</button><button type="button" class="chip" data-cf="free" aria-pressed="false">Officially free</button></div></div>
  <div class="grid" id="gCertList">{''.join(cert_cards)}</div>
 </div>
 <div class="gpane" id="g-rights">
  <div class="vhead"><h3>Know your rights</h3><p>Plain-language Ontario information under the Occupational Health and Safety Act, with section numbers you can check on e-Laws.</p></div>
  <p class="note">{esc(d["rights"]["disclaimer"])}</p>
  {''.join(rights_blocks)}
  {injured_html}
 </div>
 <div class="gpane" id="g-pay">
  <div class="vhead"><h3>Pay checker</h3><p>{esc(d["pay"]["intro"])}</p></div>
  <p class="note">{esc(d["pay"]["source"])} See also <a href="#/ohs/careers">Jobs you could get</a>.</p>
  <div class="chips noprint" id="gPayFilt" role="group" aria-label="Filter roles"><button type="button" class="chip" data-pf="Both" aria-pressed="true">Both tracks</button><button type="button" class="chip" data-pf="OHS" aria-pressed="false">OHS</button><button type="button" class="chip" data-pf="CM" aria-pressed="false">Construction management</button></div>
  <p class="count" id="gPayCount" role="status"></p>
  <div class="grid" id="gPayList">{''.join(pay_cards)}</div>
 </div>
 <div class="gpane" id="g-kit">
  <div class="vhead"><h3>Resume and interview kit</h3><p>{esc(d["kit"]["intro"])}</p></div>
  <p><a class="btn btn-t" href="samples/hhr-safety-resume-template.txt" download>Download the template (.txt)</a>
  <button class="btn btn-o" type="button" id="gCopyTmpl">Copy template</button>
  <a class="btn btn-ghost" href="#/ohs/tools/resume">Open the resume checker</a>
  <a class="btn btn-ghost" href="#/ohs/tools/interview">Open interview practice</a></p>
  <pre class="tmpl" id="gTmpl">{esc(template)}</pre>
  <h3>STAR guidance</h3>
  <div class="ggrid">{star_steps}</div>
  <h3 style="margin-top:22px">Example answers (fictional)</h3>
  {examples}
  <h3 style="margin-top:22px">Common questions</h3>
  <p>These questions already live in the interview practice tool. Filter follows your OHS or CM track, plus questions for every job seeker.</p>
  <div class="grid" id="gIvList">{''.join(qs)}</div>
 </div>
 <div class="gpane" id="g-newcomers">
  <div class="vhead"><h3>Newcomer corner</h3><p>{esc(d["newcomers"]["intro"])}</p></div>
  {''.join(new_secs)}
  <h3>Workplace safety glossary</h3>
  <p class="note">{esc(d["newcomers"]["glossary_note"])}</p>
  <label class="search noprint" for="gGlossQ"><span class="sr">Search glossary</span><input id="gGlossQ" type="search" placeholder="Search terms" autocomplete="off"></label>
  <div style="overflow:auto"><table class="gloss" id="gGloss"><thead><tr><th scope="col">English</th><th scope="col">Français</th><th scope="col">Español</th></tr></thead><tbody>{rows}</tbody></table></div>
 </div>
 <div class="gpane" id="g-toolbox">
  <div class="vhead"><h3>Toolbox talk library</h3><p>{esc(d["toolbox"]["intro"])}</p></div>
  {''.join(talks)}
 </div>
 <div class="gpane" id="g-designations">
  <div class="vhead"><h3>Designation roadmap</h3><p>{esc(d["designations"]["intro"])}</p></div>
  <p><a class="btn btn-primary" href="#/ohs/skills">Practice in Test Your Skills</a></p>
  <div class="grid">{''.join(des)}</div>
 </div>
</div></section>
'''
    return html

HOME = '''
   <div class="ghome" id="guidesHome">
    <div class="ghead"><h2 style="margin:0;font-size:1.2rem" data-i18n="guides_home_title">Workplace and career guides</h2>
    <a href="#/ohs/guides" data-nav="guides">See all guides</a></div>
    <p class="note" style="margin-bottom:14px">Free for both career tracks. Know your rights and the certification finder are always free.</p>
    <div class="ggrid">
     <a class="gcard" href="#/ohs/guides/certs" data-guide="certs"><span class="gbadge">Free</span><h3>Certification finder</h3><p>WAH, 4 Steps, 5 Steps, WHMIS and other official tickets.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/rights" data-guide="rights"><span class="gbadge">Free</span><h3>Know your rights</h3><p>OHSA rights, work refusal, reprisal, and what to do if you are hurt.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/pay" data-guide="pay"><span class="gbadge">Free</span><h3>Pay checker</h3><p>Job Bank wage ranges for safety and construction roles.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/kit" data-guide="kit"><span class="gbadge">Free</span><h3>Resume &amp; interview</h3><p>A copyable template, common questions and STAR samples.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/newcomers" data-guide="newcomers"><span class="gbadge">Free</span><h3>Newcomer corner</h3><p>Credential recognition, settlement supports, and a 3-language glossary.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/toolbox" data-guide="toolbox"><span class="gbadge">Free</span><h3>Toolbox talks</h3><p>Ready-to-use talks with CCOHS and IHSA fact-sheet links.</p><span class="go">Open</span></a>
     <a class="gcard" href="#/ohs/guides/designations" data-guide="designations"><span class="gbadge">Free</span><h3>Designations</h3><p>NCSO, CRST, CRSP, Gold Seal and CHSC, tied to Test Your Skills.</p><span class="go">Open</span></a>
    </div>
   </div>
'''

NAV = '<a href="#/ohs/guides" data-nav="guides" data-i18n="nav_guides"><svg class="i"><use href="#i-book"/></svg><span data-i18n-label>Guides</span></a>'

JS = r'''
var GUIDES=['certs','rights','pay','kit','newcomers','toolbox','designations'];
function showGuide(){
  var sub=ST.sub||'hub';
  $$('.gpane').forEach(function(p){p.classList.toggle('on',p.id==='g-'+sub)});
  $$('[data-guide]').forEach(function(a){if(a.getAttribute('data-guide')===sub)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
  if(!window._gBound){bindGuides();window._gBound=1}
  filterPay();filterCerts();filterInterview();
}
function bindGuides(){
  var q=$('#gCertQ');if(q)q.addEventListener('input',filterCerts);
  $$('#gCertFilt .chip').forEach(function(b){b.addEventListener('click',function(){$$('#gCertFilt .chip').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});filterCerts()})});
  $$('#gPayFilt .chip').forEach(function(b){b.addEventListener('click',function(){$$('#gPayFilt .chip').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});filterPay()})});
  var gq=$('#gGlossQ');if(gq)gq.addEventListener('input',function(){var s=(gq.value||'').toLowerCase();$$('#gGloss tbody tr').forEach(function(tr){tr.hidden=s&&tr.textContent.toLowerCase().indexOf(s)<0})});
  var c=$('#gCopyTmpl'),t=$('#gTmpl');
  if(c&&t)c.addEventListener('click',function(){var x=t.textContent||'';if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(x).then(function(){c.textContent='Copied';setTimeout(function(){c.textContent='Copy template'},1600)}).catch(function(){})}else{var a=document.createElement('textarea');a.value=x;document.body.appendChild(a);a.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(a);}});
}
function filterCerts(){
  var q=(($('#gCertQ')||{}).value||'').toLowerCase();
  var mode='all';$$('#gCertFilt .chip').forEach(function(b){if(b.getAttribute('aria-pressed')==='true')mode=b.getAttribute('data-cf')||'all'});
  $$('#gCertList .card').forEach(function(card){
    var text=card.textContent.toLowerCase();
    var ask=card.getAttribute('data-ask')==='1';
    var free=/^free\b/i.test((card.querySelector('.gbadge:not(.first)')||{textContent:''}).textContent||'');
    var show=(!q||text.indexOf(q)>=0)&&(mode==='all'||(mode==='first'&&ask)||(mode==='free'&&free));
    card.hidden=!show;
  });
}
function filterPay(){
  var mode='Both';$$('#gPayFilt .chip').forEach(function(b){if(b.getAttribute('aria-pressed')==='true')mode=b.getAttribute('data-pf')||'Both'});
  var n=0,tot=0;$$('#gPayList .card').forEach(function(card){tot++;var tr=card.getAttribute('data-track');var show=(mode==='Both'||tr===mode);card.hidden=!show;if(show)n++});
  var c=$('#gPayCount');if(c)c.textContent=n+' roles ('+tot+' in the Job Bank list)';
}
function filterInterview(){
  $$('#gIvList .card').forEach(function(card){var b=card.getAttribute('data-iv');card.hidden=!(b==='Both'||b.toLowerCase()===ST.track)});
}
'''

def splice_js(t: str) -> str:
    if "var GUIDES=" in t and "function showGuide()" in t:
        # already injected — leave JS functions, still ensure parse/go patched
        pass
    else:
        # insert GUIDES + functions before showTool or after TOOLS
        t = t.replace("var TOOLS=['resume','gap','interview'];", "var TOOLS=['resume','gap','interview'];\n" + JS, 1)
    # parse() sub handling
    old = "if(ST.page==='tools'&&TOOLS.indexOf(ST.sub)<0)ST.sub='resume';if(ST.page!=='tools')ST.sub='';"
    new = "if(ST.page==='tools'&&TOOLS.indexOf(ST.sub)<0)ST.sub='resume';else if(ST.page==='guides'){if(GUIDES.indexOf(ST.sub)<0)ST.sub='';}else if(ST.page!=='tools')ST.sub='';"
    if old in t:
        t = t.replace(old, new, 1)
    # updateLinks for data-guide (after data-tool block)
    tool_line = "$$('[data-tool]').forEach(function(a){a.setAttribute('href',href('tools',a.dataset.tool));if(ST.page==='tools'&&a.dataset.tool===ST.sub)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});"
    guide_line = tool_line + "\n $$('[data-guide]').forEach(function(a){var s=a.dataset.guide;a.setAttribute('href',href('guides',s&&s!=='hub'?s:''));if(ST.page==='guides'&&(s||'hub')===(ST.sub||'hub'))a.setAttribute('aria-current','page');else if(ST.page!=='guides')a.removeAttribute('aria-current')});"
    if "$$('[data-guide]')" not in t and tool_line in t:
        t = t.replace(tool_line, guide_line, 1)
    # data-pane in go()
    old_pane = "document.documentElement.setAttribute('data-view',ST.page);document.documentElement.setAttribute('data-pane',ST.page==='tools'?ST.sub:'resume');"
    new_pane = "document.documentElement.setAttribute('data-view',ST.page);document.documentElement.setAttribute('data-pane',ST.page==='guides'?(ST.sub||'hub'):(ST.page==='tools'?ST.sub:'resume'));"
    if old_pane in t:
        t = t.replace(old_pane, new_pane, 1)
    # showGuide hook
    old_show = "$$('.view').forEach(function(v){v.classList.toggle('on',v.id==='v-'+ST.page)});if(ST.page==='tools')showTool();"
    new_show = "$$('.view').forEach(function(v){v.classList.toggle('on',v.id==='v-'+ST.page)});if(ST.page==='tools')showTool();if(ST.page==='guides')showGuide();"
    if "if(ST.page==='guides')showGuide()" not in t and old_show in t:
        t = t.replace(old_show, new_show, 1)
    # focus when guides sub changes
    old_focus = "if(USERNAV&&(PREV.page!==ST.page||(ST.page==='tools'&&PREV.sub!==ST.sub)))"
    new_focus = "if(USERNAV&&(PREV.page!==ST.page||((ST.page==='tools'||ST.page==='guides')&&PREV.sub!==ST.sub)))"
    if old_focus in t:
        t = t.replace(old_focus, new_focus, 1)
    return t


def upsert_block(t: str, start: str, end: str, body: str) -> str:
    block = start + body + end
    if start in t and end in t:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda m: block, t, count=1, flags=re.S)
    return None  # type: ignore


def main() -> int:
    d = json.loads(GUIDES.read_text(encoding="utf-8"))
    t = INDEX.read_text(encoding="utf-8")
    # interview from app-data
    m = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', t, re.S)
    interview = json.loads(m.group(1)).get("INTERVIEW") or {}
    template = (ROOT / "samples/hhr-safety-resume-template.txt").read_text(encoding="utf-8")

    # 1. boot script
    old_boot = "P=['home','roadmaps','training','skills','tools','careers','finds','live','internships','jobs','library','ppe','about'],v=P.indexOf(h[1])>=0?h[1]:'home';d.setAttribute('data-trk',h[0]==='cm'?'cm':'ohs');d.setAttribute('data-view',v);d.setAttribute('data-pane',v==='tools'&&['resume','gap','interview'].indexOf(h[2])>=0?h[2]:'resume');"
    new_boot = "P=['home','roadmaps','training','skills','tools','guides','careers','finds','live','internships','jobs','library','ppe','about'],v=P.indexOf(h[1])>=0?h[1]:'home';d.setAttribute('data-trk',h[0]==='cm'?'cm':'ohs');d.setAttribute('data-view',v);d.setAttribute('data-pane',v==='guides'?(['certs','rights','pay','kit','newcomers','toolbox','designations'].indexOf(h[2])>=0?h[2]:'hub'):(v==='tools'&&['resume','gap','interview'].indexOf(h[2])>=0?h[2]:'resume'));"
    if old_boot not in t and "guides','careers'" not in t and "tools','guides'" not in t:
        # maybe already patched with slightly different string — try loose
        if ",'guides'," not in t.split("var PAGES=")[0][:2000] and "P=['home'" in t:
            raise SystemExit("boot script pattern not found")
    if old_boot in t:
        t = t.replace(old_boot, new_boot, 1)

    # 2. first-paint views
    old_view = "[data-view=ppe] #v-ppe{display:block}"
    new_view = "[data-view=ppe] #v-ppe,[data-view=guides] #v-guides{display:block}"
    if old_view in t and "[data-view=guides] #v-guides" not in t:
        t = t.replace(old_view, new_view, 1)

    # 3. CSS
    start, end = "/* ===== Guides (HHRG) ===== */", "/* ===== /Guides (HHRG) ===== */"
    css_block = start + CSS + "\n" + end
    if start in t:
        t = re.sub(re.escape(start) + r".*?" + re.escape(end), css_block, t, count=1, flags=re.S)
    else:
        needle = "/* ---------- soft launch: banner, unlock, lang, legal footer ---------- */"
        if needle not in t:
            raise SystemExit("CSS insertion point missing")
        t = t.replace(needle, css_block + "\n" + needle, 1)

    # 4. PAGES + PNAME
    t = t.replace(
        "var PAGES=['home','roadmaps','training','skills','tools','careers','finds','live','internships','jobs','library','ppe','about'];",
        "var PAGES=['home','roadmaps','training','skills','tools','guides','careers','finds','live','internships','jobs','library','ppe','about'];",
        1,
    )
    if "guides:'Guides'" not in t:
        t = t.replace("ppe:'Where to Buy PPE',about:'About'};", "ppe:'Where to Buy PPE',guides:'Guides',about:'About'};", 1)

    # 5. nav (desktop + menu) after Tools
    nav_add = "\n   " + NAV
    old_nav = '<a href="#/ohs/tools" data-nav="tools"><svg class="i"><use href="#i-tool"/></svg>Tools</a>'
    if old_nav in t and 'data-nav="guides"' not in t[t.find(old_nav):t.find(old_nav)+800]:
        t = t.replace(old_nav, old_nav + nav_add)  # both occurrences
    elif 'data-nav="guides"' not in t:
        raise SystemExit("nav Tools anchor not found")

    # 6. home block
    hs, he = "<!--HHRG-HOME-->", "<!--/HHRG-HOME-->"
    home_block = hs + HOME + he
    if hs in t:
        t = re.sub(re.escape(hs) + r".*?" + re.escape(he), home_block, t, count=1, flags=re.S)
    else:
        home_end = "   </div>\n  </div>\n </section>\n <section class=\"view\" id=\"v-roadmaps\""
        # after about/jobs two-col, still in wrap
        pin = '   </div>\n  </div>\n </section>\n <section class="view" id="v-roadmaps"'
        if pin not in t:
            raise SystemExit("home close not found")
        t = t.replace(pin, "   </div>\n" + home_block + "\n  </div>\n </section>\n <section class=\"view\" id=\"v-roadmaps\"", 1)

    # 7. main section + data
    ss, se = "<!--HHRG-SECTION-->", "<!--/HHRG-SECTION-->"
    data_tag = '<script type="application/json" id="guides-data">\n' + json.dumps(d, ensure_ascii=False, indent=2) + "\n</script>\n"
    section = ss + data_tag + build_html(d, interview, template) + se
    if ss in t:
        t = re.sub(re.escape(ss) + r".*?" + re.escape(se), lambda m: section, t, count=1, flags=re.S)
    else:
        pin = '<section class="view" id="v-careers" aria-labelledby="h-careers">'
        if pin not in t:
            raise SystemExit("v-careers not found")
        t = t.replace(pin, section + "\n" + pin, 1)

    # 8. JS
    t = splice_js(t)

    # 9. unlock lead
    reps = [
        (
            "Lifetime soft-launch access: full Test Your Skills, blueprints and study receipts. Roadmaps, training, Daily Finds and About stay free.",
            "Lifetime soft-launch access: full Test Your Skills, blueprints and study receipts. Roadmaps, training, Guides, Daily Finds and About stay free.",
        ),
        (
            "Accès unique au lancement : Testez vos compétences au complet, plans d’étude et reçus. Feuilles de route, formation, Trouvailles du jour et À propos restent gratuits.",
            "Accès unique au lancement : Testez vos compétences au complet, plans d’étude et reçus. Feuilles de route, formation, Guides, Trouvailles du jour et À propos restent gratuits.",
        ),
        (
            "Acceso único de lanzamiento: Test Your Skills completo, planes de estudio y recibos. Hojas de ruta, formación, Hallazgos del día y Acerca de siguen gratis.",
            "Acceso único de lanzamiento: Test Your Skills completo, planes de estudio y recibos. Hojas de ruta, formación, Guías, Hallazgos del día y Acerca de siguen gratis.",
        ),
    ]
    for a, b in reps:
        t = t.replace(a, b)

    # 10. i18n keys (append before week_when_lbl in each lang)
    i18n = {
        "en": {
            "nav_guides": "Guides",
            "guides_kicker": "Guides · free",
            "guides_title": "Workplace and career guides",
            "guides_lead": "Free tools for Ontario safety and construction-management job seekers: certificates, rights, wages, a resume kit, newcomer supports, toolbox talks and designation roadmaps. Official sources were checked on 25 November 2026. This is not legal advice and is not affiliated with the awarding bodies.",
            "guides_home_title": "Workplace and career guides",
        },
        "fr": {
            "nav_guides": "Guides",
            "guides_kicker": "Guides · gratuits",
            "guides_title": "Guides pour le travail et la carrière",
            "guides_lead": "Outils gratuits pour les personnes qui visent la santé-sécurité ou la gestion de construction en Ontario : certifications, droits, salaires, trousse CV, accueil des personnes nouvellement arrivées, causeries de sécurité et désignations. Sources officielles vérifiées le 25 novembre 2026. Ceci n’est pas un avis juridique.",
            "guides_home_title": "Guides pour le travail et la carrière",
        },
        "es": {
            "nav_guides": "Guías",
            "guides_kicker": "Guías · gratis",
            "guides_title": "Guías de trabajo y carrera",
            "guides_lead": "Herramientas gratuitas para quienes buscan empleo en seguridad o gestión de la construcción en Ontario: certificaciones, derechos, salarios, kit de currículum, apoyos para personas recién llegadas, charlas de seguridad y designaciones. Fuentes oficiales revisadas el 25 de noviembre de 2026. Esto no es asesoramiento jurídico.",
            "guides_home_title": "Guías de trabajo y carrera",
        },
    }
    # Insert keys before week_when_lbl in each language block if missing
    if "nav_guides:" not in t:
        t = t.replace("week_when_lbl:'Last updated'", "nav_guides:'Guides',\n    guides_kicker:'Guides · free',\n    guides_title:'Workplace and career guides',\n    guides_lead:'Free tools for Ontario safety and construction-management job seekers: certificates, rights, wages, a resume kit, newcomer supports, toolbox talks and designation roadmaps. Official sources were checked on 25 November 2026. This is not legal advice and is not affiliated with the awarding bodies.',\n    guides_home_title:'Workplace and career guides',\n    week_when_lbl:'Last updated'", 1)
        t = t.replace("week_when_lbl:'Dernière mise à jour'", "nav_guides:'Guides',\n    guides_kicker:'Guides · gratuits',\n    guides_title:'Guides pour le travail et la carrière',\n    guides_lead:'Outils gratuits pour les personnes qui visent la santé-sécurité ou la gestion de construction en Ontario : certifications, droits, salaires, trousse CV, accueil des personnes nouvellement arrivées, causeries de sécurité et désignations. Sources officielles vérifiées le 25 novembre 2026. Ceci n’est pas un avis juridique.',\n    guides_home_title:'Guides pour le travail et la carrière',\n    week_when_lbl:'Dernière mise à jour'", 1)
        t = t.replace("week_when_lbl:'Última actualización'", "nav_guides:'Guías',\n    guides_kicker:'Guías · gratis',\n    guides_title:'Guías de trabajo y carrera',\n    guides_lead:'Herramientas gratuitas para quienes buscan empleo en seguridad o gestión de la construcción en Ontario: certificaciones, derechos, salarios, kit de currículum, apoyos para personas recién llegadas, charlas de seguridad y designaciones. Fuentes oficiales revisadas el 25 de noviembre de 2026. Esto no es asesoramiento jurídico.',\n    guides_home_title:'Guías de trabajo y carrera',\n    week_when_lbl:'Última actualización'", 1)

    if "herzing" in t.lower():
        raise SystemExit("Herzing string appeared — aborting write")

    INDEX.write_text(t, encoding="utf-8")
    print("injected", INDEX, "len", len(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

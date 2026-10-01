"""Fetch OHS and construction-management postings from official APIs / syndication feeds, filter them and write jobs-live.json.
Standard library only. Keys come from environment variables (GitHub Actions secrets); a source whose key is missing is skipped.
Usage: python scripts/fetch_jobs.py [--out jobs-live.json] [--only id,id]"""
import json, os, sys, time, re, argparse, datetime, urllib.request, urllib.parse, email.utils, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jobs_filter as F
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
UA = 'HardHatRoadmapJobs/1.0 (+https://shaunthrasher1984-ui.github.io/hard-hat-roadmap/; daily, low volume)'
TZ_OFFSET = None  # dates are stored as UTC calendar dates
def get(url, data=None, headers=None, timeout=30):
    h = {'User-Agent': UA, 'Accept': '*/*'}; h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def iso_date(s):
    if not s: return None
    s = str(s).strip()
    try:
        d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        try: d = email.utils.parsedate_to_datetime(s)
        except Exception: return None
    if d.tzinfo is None: d = d.replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(datetime.timezone.utc).date().isoformat()
def strip_tracking(u):
    p = urllib.parse.urlsplit(u); q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.startswith('utm_') and k != 'feedId']
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ''))
# ---------- source kinds ----------
def sf_rss(src, queries, pause):
    """SAP SuccessFactors career-site 'Custom RSS feed': title ends with '(City, PROV, CC, ...)'."""
    out = []
    for q in queries:
        url = src['base'].rstrip('/') + '/services/rss/job/?' + urllib.parse.urlencode({'locale': 'en_US', 'keywords': q})
        root = ET.fromstring(get(url)); time.sleep(pause)
        for it in root.iter('item'):
            t = (it.findtext('title') or '').strip(); link = (it.findtext('link') or '').strip()
            m = re.match(r'^(.*)\(([^()]*)\)\s*$', t)
            if not m or not link: continue
            title, loc = m.group(1).strip(), [x.strip() for x in m.group(2).split(',')]
            country = next((x for x in loc if x in ('CA', 'US')), '')
            prov = next((F.prov_code(x) for x in loc[1:] if F.prov_code(x)), None) if country == 'CA' else None
            city = loc[0] if loc and not F.prov_code(loc[0]) else ''
            out.append(dict(title=title, employer=src['employer'], city=city.title() if city.islower() else city, prov=prov, country=country or 'XX',
                            posted=iso_date(it.findtext('pubDate')), url=strip_tracking(link), source=src['name'], construction_employer=src.get('construction_employer', False)))
    return out
def smartrecruiters(src, queries, pause):
    out = []; off = 0
    while True:
        d = json.loads(get(f"https://api.smartrecruiters.com/v1/companies/{urllib.parse.quote(src['company'])}/postings?" + urllib.parse.urlencode({'limit': 100, 'offset': off, 'country': 'ca'})))
        for j in d.get('content', []):
            l = j.get('location') or {}
            out.append(dict(title=j.get('name', ''), employer=src.get('employer') or (j.get('company') or {}).get('name', ''), city=l.get('city', ''), prov=F.prov_code(l.get('region', '')),
                            country=(l.get('country') or '').upper(), posted=iso_date(j.get('releasedDate')), source=src['name'],
                            url=f"https://jobs.smartrecruiters.com/{urllib.parse.quote(src['company'])}/{j.get('id')}", construction_employer=src.get('construction_employer', False),
                            context=' '.join(filter(None, [(j.get('industry') or {}).get('label'), (j.get('function') or {}).get('label')]))))
        off += 100; time.sleep(pause)
        if off >= d.get('totalFound', 0) or off >= 500: break
    return out
def greenhouse(src, queries, pause):
    d = json.loads(get(f"https://boards-api.greenhouse.io/v1/boards/{src['board']}/jobs")); out = []
    for j in d.get('jobs', []):
        parts = [x.strip() for x in (j.get('location') or {}).get('name', '').split(',')]
        prov = next((F.prov_code(x) for x in parts if F.prov_code(x)), None)
        out.append(dict(title=j.get('title', ''), employer=src['employer'], city=parts[0] if parts else '', prov=prov, country='CA' if prov else 'XX',
                        posted=iso_date(j.get('updated_at')), url=j.get('absolute_url', ''), source=src['name'], construction_employer=src.get('construction_employer', False)))
    return out
def lever(src, queries, pause):
    d = json.loads(get(f"https://api.lever.co/v0/postings/{src['board']}?mode=json")); out = []
    for j in d:
        loc = (j.get('categories') or {}).get('location', ''); parts = [x.strip() for x in loc.split(',')]
        prov = next((F.prov_code(x) for x in parts if F.prov_code(x)), None)
        posted = datetime.datetime.fromtimestamp(j.get('createdAt', 0) / 1000, datetime.timezone.utc).date().isoformat()
        out.append(dict(title=j.get('text', ''), employer=src['employer'], city=parts[0] if parts else '', prov=prov, country='CA' if prov else 'XX',
                        posted=posted, url=j.get('hostedUrl', ''), source=src['name'], construction_employer=src.get('construction_employer', False)))
    return out
def adzuna(src, queries, pause):
    aid, key = os.environ['ADZUNA_APP_ID'], os.environ['ADZUNA_APP_KEY']; out = []
    for q in queries:
        u = 'https://api.adzuna.com/v1/api/jobs/ca/search/1?' + urllib.parse.urlencode({'app_id': aid, 'app_key': key, 'what_phrase': q, 'max_days_old': F.MAX_AGE_DAYS,
                                                                                     'results_per_page': 50, 'sort_by': 'date', 'content-type': 'application/json'})
        d = json.loads(get(u, headers={'Accept': 'application/json'})); time.sleep(max(pause, 2.5))
        for j in d.get('results', []):
            area = (j.get('location') or {}).get('area') or []
            prov = F.prov_code(area[1]) if len(area) > 1 else None
            out.append(dict(title=re.sub(r'<[^>]+>', '', j.get('title', '')), employer=(j.get('company') or {}).get('display_name', ''), city=area[-1] if len(area) > 2 else '',
                            prov=prov, country='CA', posted=iso_date(j.get('created')), url=j.get('redirect_url', ''), source='Adzuna', attr='adzuna',
                            context=(j.get('category') or {}).get('label', '')))
    return out
def jooble(src, queries, pause):
    key = os.environ['JOOBLE_API_KEY']; out = []
    for q in queries:
        for loc in ('Ontario', 'Quebec'):
            d = json.loads(get('https://ca.jooble.org/api/' + key, data=json.dumps({'keywords': q, 'location': loc, 'page': 1}).encode(),
                               headers={'Content-Type': 'application/json'})); time.sleep(pause)
            for j in d.get('jobs', []):
                parts = [x.strip() for x in (j.get('location') or '').split(',')]
                prov = next((F.prov_code(x) for x in parts if F.prov_code(x)), None) or F.prov_code(loc)
                out.append(dict(title=re.sub(r'<[^>]+>', '', j.get('title', '')), employer=j.get('company', ''), city=parts[0] if parts and not F.prov_code(parts[0]) else '',
                                prov=prov, country='CA', posted=iso_date(j.get('updated')), url=j.get('link', ''), source='Jooble', attr='jooble'))
    return out
KINDS = dict(sf_rss=sf_rss, smartrecruiters=smartrecruiters, greenhouse=greenhouse, lever=lever, adzuna=adzuna, jooble=jooble)
ATTR = {'adzuna': {'text': 'Jobs by Adzuna', 'url': 'https://www.adzuna.ca/', 'logo': 'assets/adzuna-logo.png'},
        'jooble': {'text': 'Jobs via Jooble', 'url': 'https://ca.jooble.org/'}}
def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=os.path.join(ROOT, 'jobs-live.json')); ap.add_argument('--only', default='')
    ap.add_argument('--pause', type=float, default=1.0); ap.add_argument('--dump-raw', default=''); a = ap.parse_args(argv)
    cfg = json.load(open(os.path.join(HERE, 'jobs_sources.json'))); only = set(filter(None, a.only.split(',')))
    queries = cfg['queries']['OHS'] + cfg['queries']['CM']; raw = []; report = []
    for s in cfg['sources']:
        if only and s['id'] not in only: continue
        r = dict(id=s['id'], name=s['name'])
        if not s.get('enabled'): r['status'] = 'off'; r['why'] = s.get('terms', ''); report.append(r); continue
        miss = [k for k in s.get('needs', []) if not os.environ.get(k)]
        if miss: r['status'] = 'skipped: missing secret ' + ', '.join(miss); report.append(r); print(s['id'], r['status']); continue
        if s.get('logo') and not os.path.isfile(os.path.join(ROOT, s['logo'])):
            r['status'] = f"skipped: add the official logo at {s['logo']} (attribution rule)"; report.append(r); print(s['id'], r['status']); continue
        try:
            got = KINDS[s['kind']](s, queries, a.pause)
            for g in got:
                if s.get('attr'): g['attr'] = s['id']
            raw += got; r['status'] = 'ok'; r['fetched'] = len(got)
        except Exception as e:
            r['status'] = 'error: ' + type(e).__name__ + ': ' + str(e)[:160]
        report.append(r); print(s['id'], r['status'], r.get('fetched', ''), flush=True)
    raw = [j for j in raw if j.get('posted')]
    if a.dump_raw: json.dump(raw, open(a.dump_raw, 'w'), ensure_ascii=False)
    st = {}; jobs = F.clean(raw, stats=st)
    for r in report:
        if r['status'] == 'ok': r['kept'] = sum(1 for j in jobs if j['source'] == r['name'])
    ok_sources = [r for r in report if r['status'] == 'ok']
    if not ok_sources and os.path.exists(a.out) and not only:
        print('No source succeeded; keeping the previous file.'); return 1
    attr = {k: v for k, v in ATTR.items() if any(j.get('attr') == k for j in jobs)}
    for s in cfg['sources']:
        if s.get('attr') and any(j.get('attr') == s['id'] for j in jobs): attr[s['id']] = {'text': s['attr']}
    out = dict(schema=1, generated_at=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
               max_age_days=F.MAX_AGE_DAYS, cap=F.CAP, counts={'OHS': sum(j['track'] == 'OHS' for j in jobs), 'CM': sum(j['track'] == 'CM' for j in jobs)},
               sources=[{k: v for k, v in r.items() if k in ('id', 'name', 'status', 'fetched', 'kept')} for r in report], attribution=attr, filter_stats=st, jobs=jobs)
    tmp = a.out + '.tmp'; json.dump(out, open(tmp, 'w'), ensure_ascii=False, indent=0, separators=(',', ':')); os.replace(tmp, a.out)
    print(json.dumps({k: out[k] for k in ('generated_at', 'counts', 'filter_stats')}, ensure_ascii=False)); return 0
if __name__ == '__main__': sys.exit(main())

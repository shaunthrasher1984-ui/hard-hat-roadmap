"""Sanity check for jobs-live.json before the workflow commits it. Exit 1 on any problem."""
import json, sys, re, datetime, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jobs_filter as F
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'jobs-live.json')); bad = []
now = datetime.datetime.now(datetime.timezone.utc)
if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', d.get('generated_at', '')): bad.append('generated_at')
if len(d.get('jobs', [])) > F.CAP: bad.append('over cap')
for j in d.get('jobs', []):
    for k in ('id', 'title', 'employer', 'posted', 'source', 'url', 'track', 'region'):
        if not j.get(k) and k != 'employer': bad.append(f'{k} missing in {j.get("id")}')
    if j.get('track') not in ('OHS', 'CM'): bad.append('track ' + str(j.get('track')))
    if j.get('region') not in ('ON', 'QC', 'CA'): bad.append('region ' + str(j.get('region')))
    if not str(j.get('url', '')).startswith('https://'): bad.append('url ' + str(j.get('url')))
    if F.age_days(j['posted'], now) > F.MAX_AGE_DAYS: bad.append('too old ' + j['id'])
    if F.blocked(j['title'], j.get('employer', ''), j.get('city', '')): bad.append('blocked text in ' + j['id'])
    if j.get('attr') == 'adzuna' and not os.path.isfile(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'adzuna-logo.png')): bad.append('Adzuna logo missing')
print('jobs-live.json:', len(d.get('jobs', [])), 'postings,', 'OK' if not bad else 'PROBLEMS: ' + '; '.join(bad[:10])); sys.exit(1 if bad else 0)

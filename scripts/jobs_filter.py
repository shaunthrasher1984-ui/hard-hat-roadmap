"""Filter logic for the Live job postings list (pure functions, no network; unit-tested with sample data).
classify() -> 'OHS' | 'CM' | None, then clean(): drop blocked, non-Canada, older than MAX_AGE_DAYS, de-duplicate, cap."""
import re, json, os, hashlib, datetime
MAX_AGE_DAYS = 30
CAP = 150
# ---- OHS (occupational health and safety) ----
OHS_RX = [r'\bhealth\s*(?:and|&|\+)\s*safety\b', r'\bh\s*&\s*s\b', r'\b(?:ohs|ehs|hse|she|qhse|hsse|ohse|hs&e|eh&s|oh&s|ehss)\b',
    r'\bsafety\s+(?:co-?ordinator|officer|advis[eo]r|specialist|manager|lead|leader|supervisor|consultant|trainer|instructor|technician|technologist|'
    r'representative|rep|professional|student|co-?op|intern|internship|administrator|associate|director|partner|generalist|auditor|inspector|program)',
    r'\b(?:site|construction|workplace|occupational|industrial|field|corporate|regional|project)\s+safety\b',
    r'\boccupational\s+(?:health|hygien)', r'\bindustrial\s+hygien', r'\breturn[\s-]*to[\s-]*work\b', r'\bdisability\s+management\b',
    r'\bjhsc\b', r'\bcrsp\b', r'\bcrst\b', r'\benvironment(?:al)?,?\s*(?:health|safety)\b', r'\bradiation\s+(?:safety|protection)\b',
    r'\bsafety\s*(?:&|and)\s*(?:training|compliance|environment|quality|wellness|risk)\b', r'\bprevention\s+(?:consultant|advisor|specialist)\b',
    r'\bsant[ée]\s+(?:et|&)\s+s[ée]curit[ée]', r'\bsst\b', r'pr[ée]ventionniste', r'\bconseill(?:er|[èe]re)\s+(?:en\s+)?(?:pr[ée]vention|sst)']
OHS_EXCL = [r'\bfood\b', r'cyber', r'\binformation\s+security\b', r'\bit\s+security\b', r'\bsecurity\s+(?:guard|officer|analyst|engineer)\b', r'\bsoftware\b',
    r'\bdata\b', r'\bpatient\s+safety\b', r'\bdrug\b', r'pharmacovigilance', r'\bclinical\b', r'\bproduct\s+safety\b', r'\bflight\b', r'\baviation\b',
    r'\bnuclear\s+safety\b', r'\breactor\b', r'\bsafety\s+(?:analysis|case|assessment\s+engineer)\b', r'\bfunctional\s+safety\b', r'\broad\s+safety\b',
    r'\btraffic\b', r'\bpublic\s+safety\b', r'\bschool\b', r'\bchild', r'\blife\s+safety\b', r'\bfire\b', r'\btrust\s*(?:and|&)\s*safety\b',
    r'\bcontent\b', r'safety[\s-]sensitive', r'\blifeguard\b', r'\bpool\b', r'\bwater\s+safety\b', r'\belectrical\s+safety\b', r'\bpsychotherap',
    r'\bnurs(?:e|ing)\b', r'\bphysician\b', r'\bveterinar', r'\bpolice\b', r'\bparamedic\b', r'\bcommunity\s+safety\b', r'\bsafety\s+net\b', r'\bsales\b']
# ---- CM (construction management) ----
CM_STRONG = [r'\bassistant\s+project\s+manager\b', r'\bfield\s+engineer', r'\bsite\s+engineer', r'\bconstruction\s+(?:manager|management|supervisor|co-?ordinator|'
    r'administrator|project|superintendent|director|lead|scheduler|planner|estimator|student|co-?op|intern|inspector|engineer|contract)',
    r'\bsite\s+(?:supervisor|superintendent|manager|super)\b', r'\bsuperintendent\b', r'\b(?:junior\s+|senior\s+|lead\s+|cost\s+|construction\s+)?estimator\b',
    r'\bestimating\b', r'\bquantity\s+surveyor', r'\bgeneral\s+superintendent\b', r'\bproject\s+controls?\b', r'\bcost\s+control', r'\bpre-?construction\b',
    r'\bsuperintendant\b', r'\bsurintendant', r'\bestimat(?:eur|rice)', r'\bdirect(?:eur|rice)\S*\s+(?:de\s+)?(?:la\s+)?construction\b', r'\b(?:bim|vdc)\s+(?:co-?ordinator|manager|lead|specialist)']
CM_GENERIC = [r'\bproject\s+(?:co-?ordinator|manager|engineer|administrator|director|scheduler|planner|lead|leader|management)\b', r'\bscheduler\b',
    r'\bplanner\b', r'\bcontract\s+administrator\b', r'\bproject\s+(?:co-?op|student|intern)', r'\bplanning\s+manager\b',
    r'\b(?:manager|co-?ordinator|administrator|engineer|director|lead)\s*,\s*(?:\w+\s+)?projects?\b', r'\bcoordonn?at(?:eur|rice)\s+de\s+projets?\b',
    r'\bgestionnaire,?\s+(?:de\s+)?projets?\b', r'\bcharg[ée]e?\s+de\s+projets?\b', r'\bing[ée]nieur(?:e)?\s+de\s+projets?\b']
CM_CONTEXT = r'\b(?:construction|site|field|capital|infrastructure|civil|building|buildings|facilit\w*|renovation|ici|highway|bridge|transit|rail|' \
    r'wastewater|water|mechanical|electrical|structural|concrete|contractor|design[\s-]build|transmission|substation|pipeline|roads?|tunnel|utilit\w*|' \
    r'general\s+contractor|residential|commercial|institutional|industrial|heavy\s+civil|builds?)\b'
CM_EXCL = [r'\bsoftware\b', r'\bit\b', r'\binformation\s+technology\b', r'\bdigital\b', r'\bmarketing\b', r'\bclinical\b', r'\bresearch\b', r'\bdata\b',
    r'\bevents?\b', r'\bfundrais', r'\bhuman\s+resources\b', r'\bpayroll\b', r'\bfinanc', r'\binsurance\b', r'\bclaims?\b', r'\bauto\s*body\b', r'\bcollision\b',
    r'\bpharma', r'\bretail\b', r'\bstore\b', r'\brestaurant\b', r'\bhospitality\b', r'\bbuilding\s+superintendent\b', r'\bproperty\b', r'\bcondo',
    r'\bcustodian\b', r'\bsuperintendent\s+of\s+(?:education|schools?)\b', r'\bschool\s+superintendent\b', r'\bmortgage\b', r'\bloan\b', r'\bprint', r'\bmedia\b',
    r'\bsales\b', r'\bproduction\s+(?:planner|scheduler)\b', r'\bmaterials?\s+planner\b', r'\bdemand\s+planner\b', r'\bsupply\s+chain\b', r'\bwedding\b',
    r'\btravel\b', r'\bmeeting\b', r'\bcommunications?\b', r'\bpolicy\b', r'\bprogram\s+planner\b', r'\bland\s+use\b', r'\burban\s+planner\b',
    r'\btransportation\s+planner\b', r'\bcommunity\s+planner\b', r'\bcharge\s+nurse\b', r'\bpolicy\s+planner\b', r'\bsap\b', r'\berp\b', r'\bcloud\b']
OHS_NOC = {'22232'}; CM_NOC = {'70010', '22303'}
def _any(rxs, s): return any(re.search(r, s, re.I) for r in rxs)
def classify(title, employer='', noc='', construction_employer=False, context=''):
    t = ' '.join(str(title or '').split())
    if not t: return None
    if noc and str(noc) in OHS_NOC and not _any(OHS_EXCL, t): return 'OHS'
    if _any(OHS_RX, t) and not _any(OHS_EXCL, t): return 'OHS'
    if _any(CM_EXCL, t): return None
    if noc and str(noc) in CM_NOC: return 'CM'
    if _any(CM_STRONG, t): return 'CM'
    if _any(CM_GENERIC, t) and (construction_employer or re.search(CM_CONTEXT, t + ' ' + (context or ''), re.I)): return 'CM'
    return None
# ---- privacy / site-wording blocklist (hashed, so the names are never published) ----
_BL = None
def _norm(s): return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower().replace('&', ' and ')).strip()
def _h(s): return hashlib.sha256(s.encode()).hexdigest()
def load_blocklist(path=None):
    global _BL
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blocklist_sha256.json')
    d = json.load(open(path)); _BL = (set(d['sub']), sorted(set(d['sub_lens'])), set(d['gram'])); return _BL
def blocked(*texts):
    sub, lens, gram = _BL or load_blocklist()
    w = _norm(' '.join(str(x or '') for x in texts)).split()
    for n in (1, 2, 3):
        for i in range(len(w) - n + 1):
            if _h(' '.join(w[i:i + n])) in gram: return True
    joined = [''.join(w[i:i + k]) for k in (1, 2, 3) for i in range(len(w) - k + 1)]
    for tok in joined:
        for L in lens:
            for i in range(len(tok) - L + 1):
                if _h(tok[i:i + L]) in sub: return True
    return False
# ---- locations ----
PROV = {'ON': 'Ontario', 'QC': 'Quebec', 'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 'SK': 'Saskatchewan', 'NS': 'Nova Scotia',
        'NB': 'New Brunswick', 'NL': 'Newfoundland and Labrador', 'PE': 'Prince Edward Island', 'YT': 'Yukon', 'NT': 'Northwest Territories', 'NU': 'Nunavut'}
_PN = {_norm(v): k for k, v in PROV.items()}; _PN.update({'quebec': 'QC', 'qu bec': 'QC', 'pei': 'PE', 'newfoundland': 'NL', 'nwt': 'NT'})
def prov_code(s):
    s = str(s or '').strip()
    if s.upper() in PROV: return s.upper()
    n = _norm(s.replace('é', 'e').replace('É', 'E'))
    return _PN.get(n)
def region_of(prov): return prov if prov in ('ON', 'QC') else 'CA'
# ---- dates ----
def age_days(posted, now):
    d = datetime.date.fromisoformat(posted); return (now.date() - d).days
# ---- pipeline ----
def dedupe_key(j): return (_norm(j['title']), _norm(j['employer']), _norm(j.get('city', '')))
def clean(jobs, now=None, max_age=MAX_AGE_DAYS, cap=CAP, stats=None):
    """jobs: dicts with title, employer, city, prov, country, posted (YYYY-MM-DD), url, source, track (or None to classify)."""
    now = now or datetime.datetime.now(datetime.timezone.utc); st = stats if stats is not None else {}
    for k in ('in', 'not_canada', 'no_track', 'blocked', 'too_old', 'bad_date', 'bad_url', 'duplicate', 'over_cap', 'kept'): st.setdefault(k, 0)
    best = {}; seen_url = set()
    for j in jobs:
        st['in'] += 1
        if (j.get('country') or 'CA').upper() not in ('CA', 'CAN', 'CANADA') or (j.get('prov') and j['prov'] not in PROV):
            st['not_canada'] += 1; continue
        tr = j.get('track') or classify(j['title'], j.get('employer', ''), j.get('noc', ''), j.get('construction_employer', False), j.get('context', ''))
        if tr not in ('OHS', 'CM'): st['no_track'] += 1; continue
        if blocked(j['title'], j.get('employer', ''), j.get('city', '')): st['blocked'] += 1; continue
        try: a = age_days(j['posted'], now)
        except Exception: st['bad_date'] += 1; continue
        if a > max_age or a < -2: st['too_old'] += 1; continue
        if not re.match(r'^https://', str(j.get('url', ''))): st['bad_url'] += 1; continue
        u = j['url'].split('#')[0]
        if u in seen_url: st['duplicate'] += 1; continue
        seen_url.add(u)
        out = dict(title=' '.join(j['title'].split())[:140], employer=' '.join(str(j.get('employer', '')).split())[:90], city=' '.join(str(j.get('city', '')).split())[:60],
                   prov=j.get('prov') or '', region=region_of(j.get('prov')), track=tr, posted=j['posted'], source=j['source'], url=u)
        if j.get('attr'): out['attr'] = j['attr']
        k = dedupe_key(out)
        if k in best:
            st['duplicate'] += 1
            if out['posted'] > best[k]['posted']: best[k] = out
            continue
        best[k] = out
    L = sorted(best.values(), key=lambda j: (j['posted'], j['title']), reverse=True)
    # cap: keep up to half the cap per track first, then fill by date so one track cannot crowd out the other
    half = cap // 2; keep = []; per = {'OHS': 0, 'CM': 0}; rest = []
    for j in L:
        if per[j['track']] < half: keep.append(j); per[j['track']] += 1
        else: rest.append(j)
    keep += rest[:max(0, cap - len(keep))]; st['over_cap'] += len(L) - len(keep)
    keep.sort(key=lambda j: (j['posted'], j['title']), reverse=True)
    for i, j in enumerate(keep): j['id'] = hashlib.sha1((j['url'] + j['title']).encode()).hexdigest()[:10]
    st['kept'] = len(keep); return keep

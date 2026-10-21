# build_site.py — one command builds the whole deployable site into ./site/
#   python3 build_site.py
# Outputs (upload the CONTENTS of site/ to the GitHub repo root):
#   index.html (keys injected from keys.json if present), db.js, robots.txt, sitemap.xml,
#   colleges/index.html + colleges/{state}.html + colleges/ncaa-{div}.html
# Also writes My-University-View.html (empty keys) alongside for local testing.
import json, os, re, html as H

DOMAIN = 'https://www.myuniview.com'
STATE_NAMES = {
 'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut',
 'DE':'Delaware','DC':'Washington DC','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois',
 'IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland',
 'MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana',
 'NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York',
 'NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania',
 'RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah',
 'VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming',
 'PR':'Puerto Rico','GU':'Guam','VI':'US Virgin Islands','AS':'American Samoa','MP':'Northern Mariana Islands',
 'FM':'Micronesia','MH':'Marshall Islands','PW':'Palau',
}
DIVS = {'D-I':('ncaa-d1','NCAA Division I'),'D-II':('ncaa-d2','NCAA Division II'),
        'D-III':('ncaa-d3','NCAA Division III'),'NAIA':('naia','NAIA')}

def slug(name): return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',name.lower())).strip('-')

CSS = """:root{--bg:#0f172a;--panel:#1e293b;--line:#334155;--text:#e2e8f0;--dim:#94a3b8;--acc:#60A5FA}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.wrap{max-width:860px;margin:0 auto;padding:5vh 5vw}
.logo{font-weight:800;font-size:18px;margin-bottom:24px}.logo span{color:var(--acc)}.logo a{color:var(--text);text-decoration:none}
h1{font-size:28px;margin-bottom:6px}
.sub{color:var(--dim);margin-bottom:18px;font-size:15px}
.cta{display:inline-block;background:var(--acc);color:#0f172a;font-weight:700;padding:10px 18px;border-radius:10px;text-decoration:none;margin:6px 0 22px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:8px 8px;text-align:left;vertical-align:top}
th{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.4px}
a{color:var(--acc)}
h2{font-size:19px;margin:26px 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px;margin:14px 0}
.grid a{font-size:14px;text-decoration:none}
footer{color:var(--dim);font-size:12px;margin-top:44px;border-top:1px solid var(--line);padding-top:14px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.fact{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.fact b{display:block;font-size:18px;color:var(--text)}
.fact span{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.4px}
.crumb{font-size:12px;color:var(--dim);margin-bottom:10px}
.crumb a{color:var(--dim)}
.bar{background:var(--panel);border-radius:4px;height:8px;overflow:hidden;margin-top:3px}
.bar i{display:block;height:100%;background:var(--acc)}
.mj{margin:4px 0 10px}
.mj div{font-size:13px}
.cta2{display:inline-block;border:1px solid var(--acc);color:var(--acc);padding:8px 14px;border-radius:9px;text-decoration:none;margin:4px 8px 4px 0;font-size:14px}
@media (prefers-color-scheme: light){:root{--bg:#f6f8fb;--panel:#ffffff;--line:#cbd5e1;--text:#0f172a;--dim:#5b6b80;--acc:#1B5FCC}}"""

# Cookieless Umami tag. Empty unless keys.json carries a "umami" website id, so a build
# without the key is identical to the builds that came before it.
ANALYTICS = ''

def umami_tag(website_id):
    if not website_id: return ''
    # data-exclude-hash is essential here, not cosmetic: Supabase OAuth returns the user to
    # /#access_token=<JWT>, and without it the tracker records that whole URL. The JWT is
    # base64 and decodes to the user's email, so sign-ins would write access tokens and
    # personal data into a third-party analytics service.
    # data-exclude-search drops ?upgraded=1 and similar from Stripe returns.
    return ('<script defer src="https://cloud.umami.is/script.js" '
            'data-website-id="%s" data-exclude-hash="true" '
            'data-exclude-search="true"></script>' % H.escape(website_id))

def page(title, desc, canonical, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y="80" font-size="80">🎓</text></svg>'>
{ANALYTICS}
<style>{CSS}</style>
</head>
<body><div class="wrap">
<div class="logo"><a href="/">🎓 My <span>University View</span></a></div>
{body}
<footer>Data: US Dept. of Education College Scorecard / IPEDS (2022–23) · Athletics from NCAA/NCSA public listings · Always verify with each college ·
<a href="/app/">Interactive map</a> · <a href="/colleges/">All states</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a> · © Sean Brady</footer>
</div></body></html>"""

def href(s):
    u = re.sub(r'^(https?:/+)+', '', s.get('url') or '')   # strip any pre-existing scheme(s)
    return 'https://' + H.escape(u)

def money(v): return f'${v:,}' if isinstance(v,int) else '—'
def pct(v): return f'{round(v*100,1)}%' if isinstance(v,(int,float)) else '—'

def school_rows(schools, show_div=True, state_slug=None):
    out = ['<table><tr><th>School</th><th>City</th><th>Type</th><th>Tuition (in-state)</th><th>Avg net cost</th>%s</tr>' % ('<th>Athletics</th>' if show_div else '')]
    for s in schools:
        nm = (f'<a href="/colleges/{state_slug}/{s.get("_slug") or slug(s["n"])}.html">{H.escape(s["n"])}</a>' if state_slug
              else (f'<a href="{href(s)}" rel="noopener nofollow">{H.escape(s["n"])}</a>' if s.get('url') else H.escape(s['n'])))
        ath = s.get('ad') or ('NCAA' if s.get('sb') else '—')
        out.append(f'<tr><td>{nm}</td><td>{H.escape(s["c"])}</td><td>{s["ctrl"]} · {s["lvl"]}</td><td>{money(s.get("tin"))}</td><td>{money(s.get("np"))}</td>%s</tr>' % (f'<td>{ath}</td>' if show_div else ''))
    out.append('</table>')
    return '\n'.join(out)


def money(v): return f'${v:,}' if isinstance(v,(int,float)) and v else None

def school_page(s, db, state_name, state_slug, peers):
    """One page per school. Content is drawn from federal data, so every page differs."""
    nm = H.escape(s['n']); city = H.escape(s['c']); st = s['s']
    lvl = s['lvl']; ctrl = s['ctrl']
    kind = '2-year college' if lvl == '2-year' else 'university'
    facts = []
    if s.get('en'): facts.append((f"{s['en']:,}", 'Undergraduates'))
    if isinstance(s.get('adm'), (int, float)): facts.append((f"{round(s['adm']*100)}%", 'Acceptance rate'))
    if s.get('sat'): facts.append((f"{s['sat']:,}", 'Average SAT'))
    if s.get('np'): facts.append((money(s['np']), 'Avg net cost / yr'))
    factbox = '<div class="facts">' + ''.join(
        f'<div class="fact"><b>{v}</b><span>{k}</span></div>' for v, k in facts) + '</div>' if facts else ''

    rows = []
    for label, val, note in [
        ('Tuition &amp; fees (in-state)', money(s.get('tin')), 'Published rate before aid'),
        ('Tuition &amp; fees (out-of-state)', money(s.get('tout')), 'Published rate before aid'),
        ('Room &amp; board (on campus)', money(s.get('rb')), 'Annual'),
        ('Books &amp; supplies', money(s.get('bk')), 'Estimated annual'),
        ('Total sticker cost', money(s.get('cst')), 'Everything, before aid'),
        ('<b>Average actual cost paid</b>', f"<b>{money(s.get('np'))}</b>" if s.get('np') else None,
         '<b>Average paid after grants and scholarships — an average, not a quote</b>'),
    ]:
        if val: rows.append(f'<tr><td>{label}</td><td>{val}</td><td style="color:var(--dim);font-size:13px">{note}</td></tr>')
    cost = ('<h2>What ' + nm + ' actually costs</h2><table><tr><th>Item</th><th>Amount</th><th></th></tr>'
            + ''.join(rows) + '</table>') if rows else ''
    if s.get('cst') and s.get('np') and s['cst'] > s['np']:
        cost += (f'<p class="sub" style="margin-top:8px">Across all students, the average paid here was '
                 f'<b>{money(s["cst"]-s["np"])} less</b> than the sticker price — about '
                 f'{round((1-s["np"]/s["cst"])*100)}% off, once grants and scholarships are counted. '
                 f'Individual awards vary enormously, and many students receive nothing at all.</p>')
    cost += ('<div class="note" style="margin-top:12px;border-left:3px solid var(--acc);padding:10px 12px;'
             'background:var(--panel);border-radius:8px;font-size:13.5px;line-height:1.6">'
             '<b>Do your own due diligence on cost.</b> Every figure above is a historical federal average '
             'for all students at this college. <b>No student pays the average.</b> What you are charged '
             'depends on your family&rsquo;s income and assets, your academic record, the year you apply, and '
             'what aid this college has available &mdash; and it changes year to year. Use these numbers to '
             'decide which colleges are worth investigating, never to decide what one will cost you. '
             'Run the college&rsquo;s own <a href="https://collegecost.ed.gov/net-price" target="_blank" '
             'rel="noopener">net price calculator</a> &mdash; every US college is required by law to publish '
             'one &mdash; then confirm in writing with its financial aid office before committing to anything. '
             'We are not financial, admissions or tax advisers and have no relationship with this college.'
             '</div>')

    mj = ''
    if s.get('mj'):
        tot = sum(n for _, n in s['mj']) or 1
        items = ''.join(
            f'<div>{H.escape(db["majors"][c])} — {n}%<div class="bar"><i style="width:{min(100,int(n/max(1,s["mj"][0][1])*100))}%"></i></div></div>'
            for c, n in s['mj'][:8] if c < len(db['majors']))
        if items: mj = f'<h2>Most popular fields of study</h2><div class="mj">{items}</div>' +                        '<p class="sub" style="font-size:13px">Share of degrees awarded, US Dept. of Education.</p>'

    ath = ''
    if s.get('sp'):
        SPORT_LABEL = {'baseball':'Baseball','basketball':'Basketball','xc':'Cross Country','football':'Football',
          'golf':'Golf','hockey':'Ice Hockey','lax':'Lacrosse','soccer':'Soccer','swim':'Swimming & Diving',
          'tennis':'Tennis','track':'Track & Field','wrestling':'Wrestling','softball':'Softball','vb':'Volleyball',
          'beachvb':'Beach Volleyball','fieldhockey':'Field Hockey','gym':'Gymnastics','rowing':'Rowing',
          'bowling':'Bowling','fencing':'Fencing','rifle':'Rifle','skiing':'Skiing','waterpolo':'Water Polo',
          'equestrian':'Equestrian','archery':'Archery','badminton':'Badminton','rodeo':'Rodeo','sailing':'Sailing',
          'squash':'Squash','tabletennis':'Table Tennis','weightlifting':'Weightlifting','synchroswim':'Synchronised Swimming'}
        men, women = [], []
        for k, n in sorted(s['sp'].items(), key=lambda x: -x[1]):
            lbl = SPORT_LABEL.get(k[2:], k[2:].title())
            (men if k.startswith('m-') else women).append(f'{lbl} ({n})')
        rows2 = []
        if s.get('ad'): rows2.append(f'<tr><td>Athletic association</td><td>{H.escape(s["ad"])}</td></tr>')
        if men: rows2.append(f'<tr><td>Men&rsquo;s varsity sports ({len(men)})</td><td>{H.escape(", ".join(men))}</td></tr>')
        if women: rows2.append(f'<tr><td>Women&rsquo;s varsity sports ({len(women)})</td><td>{H.escape(", ".join(women))}</td></tr>')
        sb = s.get('sb') or {}
        if sb.get('conf'): rows2.append(f'<tr><td>Softball conference</td><td>{H.escape(sb["conf"])}</td></tr>')
        if sb.get('coach'): rows2.append(f'<tr><td>Head softball coach</td><td>{H.escape(sb["coach"])}</td></tr>')
        ath = ('<h2>Varsity athletics at ' + nm + '</h2><table>' + ''.join(rows2) + '</table>'
               '<p class="sub" style="font-size:13px">Squad sizes in brackets, from the federal Equity in Athletics survey (2024&ndash;25). '
               'Filter by sport and division on the <a href="/app/">interactive map</a>.</p>')
    elif s.get('ad') or s.get('sb'):
        bits = []
        if s.get('ad'): bits.append(f'<tr><td>Athletic association</td><td>{H.escape(s["ad"])}</td></tr>')
        sb = s.get('sb') or {}
        if sb.get('conf'): bits.append(f'<tr><td>Conference (softball)</td><td>{H.escape(sb["conf"])}</td></tr>')
        if sb.get('coach'): bits.append(f'<tr><td>Head softball coach</td><td>{H.escape(sb["coach"])}</td></tr>')
        if sb.get('w') is not None and (sb.get('w') or sb.get('l')):
            bits.append(f'<tr><td>Softball record</td><td>{sb["w"]}&ndash;{sb["l"]}'
                        + (f' ({sb["season"]})' if sb.get('season') else '') + '</td></tr>')
        if bits:
            ath = ('<h2>Athletics</h2><table>' + ''.join(bits) + '</table>'
                   '<p class="sub" style="font-size:13px">Filter by sport and division on the '
                   '<a href="/app/">interactive map</a> to compare programmes and reach coaching staff.</p>')

    peer_links = ' · '.join(f'<a href="/colleges/{state_slug}/{p.get("_slug") or slug(p["n"])}.html">{H.escape(p["n"])}</a>' for p in peers)
    nearby = f'<h2>Other colleges in {state_name}</h2><p style="font-size:14px">{peer_links}</p>' if peer_links else ''

    ld = {"@context": "https://schema.org", "@type": "CollegeOrUniversity", "name": s['n'],
          "address": {"@type": "PostalAddress", "addressLocality": s['c'], "addressRegion": st, "addressCountry": "US"},
          "url": href(s)}
    if s.get('lat'): ld["geo"] = {"@type": "GeoCoordinates", "latitude": s['lat'], "longitude": s['lon']}

    setting = (' · ' + H.escape(s['loc'])) if s.get('loc') else ''
    body = f"""<div class="crumb"><a href="/">Home</a> › <a href="/colleges/">Colleges</a> › <a href="/colleges/{state_slug}.html">{state_name}</a> › {nm}</div>
<h1>{nm}</h1>
<p class="sub">{city}, {st} · {H.escape(ctrl)} {kind}{setting}</p>
{factbox}
<a class="cta" href="/app/">See {nm} on the map →</a>
<a class="cta2" href="{href(s)}" rel="noopener nofollow">Official website</a>
{cost}
{mj}
{ath}
<h2>Plan a visit and compare</h2>
<p style="font-size:14px">Add {nm} to your shortlist, score it against other colleges side by side, and plan a campus visit route from your front door with the free <a href="/app/">My University View</a> map.</p>
{nearby}
<script type="application/ld+json">{json.dumps(ld)}</script>"""

    desc = f"{s['n']} in {s['c']}, {st}: "
    if s.get('np'): desc += f"average actual cost {money(s['np'])} per year"
    elif s.get('tin'): desc += f"tuition {money(s['tin'])}"
    else: desc += f"{ctrl} {kind}"
    if isinstance(s.get('adm'), (int, float)): desc += f", {round(s['adm']*100)}% acceptance rate"
    if s.get('ad'): desc += f", {s['ad']} athletics"
    desc += ". Full cost breakdown, majors and admissions data."
    title = f"{s['n']} — Cost, Admissions & Majors ({s['c']}, {st})"
    return page(title, desc[:300], f'{DOMAIN}/colleges/{state_slug}/{s.get("_slug") or slug(s["n"])}.html', body)


def main():
    db = json.load(open('db.json'))
    schools = db['schools']
    os.makedirs('site/colleges', exist_ok=True)

    t = open('app_template.html').read()
    # Standalone / Capacitor copy keeps RELATIVE asset paths: the iOS bundle loads from
    # file://, where a leading slash resolves to the device root and nothing loads.
    open('site/My-University-View.html','w').write(t)

    keys = None
    if os.path.exists('keys.json'): keys = json.load(open('keys.json'))
    app = t
    if keys:
        app = app.replace('const SUPABASE_URL = "";       // e.g. "https://abcdefgh.supabase.co"', f'const SUPABASE_URL = "{keys["url"]}";')
        app = app.replace('const SUPABASE_ANON_KEY = "";  // the "anon public" API key', f'const SUPABASE_ANON_KEY = "{keys["anon"]}";')
    global ANALYTICS
    ANALYTICS = umami_tag((keys or {}).get('umami', ''))
    app = app.replace('<!--ANALYTICS-->', ANALYTICS)

    # Hosted copy moves to /app/, so its relative asset paths have to become absolute or
    # they resolve to /app/libs/... and 404. Done here, not in the template, so the
    # standalone and iOS builds above keep the relative paths they need.
    # Rewrite EVERY libs/ reference, not just <script src>: the Leaflet and MarkerCluster
    # stylesheets use href=, and supabase.js / xlsx are loaded from single-quoted JS
    # strings. Missing the stylesheets is silent — the JS runs, the map "works", but
    # without Leaflet's CSS the panes have no positioning, so tiles land at wrong
    # offsets and markers never appear.
    n_libs = app.count('"libs/') + app.count("'libs/")
    assert n_libs >= 7, f'expected at least 7 libs/ refs, found {n_libs}'
    app = app.replace('"libs/', '"/libs/').replace("'libs/", "'/libs/")
    assert 'src="db.js"' in app
    app = app.replace('src="db.js"', 'src="/db.js"')
    assert app.count("'careers.js'")==1 and app.count("'programs.js'")==1, 'career data paths missing from template'
    app = app.replace("'careers.js'", "'/careers.js'").replace("'programs.js'", "'/programs.js'")
    for stray in ('"libs/', "'libs/", 'src="db.js"'):
        assert stray not in app, f'relative asset path survived the rewrite: {stray}'
    # NB: not 'page' as the loop name — that shadows the module-level page() builder
    # for the whole of main(), and every later call to it fails.
    for leg in ('privacy', 'terms', 'disclaimer', 'sources', 'groups', 'contact'):
        app = app.replace(f'href="{leg}.html"', f'href="/{leg}.html"')
    assert 'src="libs/' not in app and 'src="db.js"' not in app
    os.makedirs('site/app', exist_ok=True)
    open('site/app/index.html','w').write(app)

    # Crawlable path from the homepage into the static college pages. The app navigates
    # with JavaScript, so without these the built pages are reachable only via sitemap.xml,
    # which is why Search Console reported them "Discovered - currently not indexed".
    present = {s['s'] for s in schools}
    state_nav = ' · '.join(
        f'<a href="/colleges/{slug(name)}.html">{H.escape(name)}</a>'
        for st, name in STATE_NAMES.items() if st in present)
    state_nav += f' · <a href="/colleges/">All colleges</a>'

    home = open('homepage.html').read()
    home = home.replace('<!--ANALYTICS-->', ANALYTICS)
    home = home.replace('<!--STATELINKS-->', state_nav)
    assert '<!--STATELINKS-->' not in home, 'state link placeholder not substituted'
    open('site/index.html','w').write(home)

    open('site/db.js','w').write('window.__DBDATA=' + json.dumps(db, separators=(',',':')) + ';')

    # Career search data (built by build_careers.py). careers.js is the small career index every
    # visitor loads; programs.js (school x program lists) is only fetched once Premium is active.
    if os.path.exists('careers.json'):
        cj = json.load(open('careers.json'))
        progs = cj.pop('programs')
        open('site/careers.js','w').write('window.__CAREERS=' + json.dumps(cj, separators=(',',':')) + ';')
        open('site/programs.js','w').write('window.__PROGRAMS=' + json.dumps(progs, separators=(',',':')) + ';')
    else:
        print('WARN careers.json missing — run build_careers.py; Career search will show an error')

    n_school=[0]
    urls = [f'{DOMAIN}/', f'{DOMAIN}/app/', f'{DOMAIN}/colleges/']
    for p in ('privacy','terms','disclaimer','contact','sources'): urls.append(f'{DOMAIN}/{p}.html')

    # state pages
    by_state = {}
    for s in schools: by_state.setdefault(s['s'], []).append(s)
    state_links = []
    for st, name in STATE_NAMES.items():
        ss = sorted(by_state.get(st, []), key=lambda x: x['n'])
        if not ss: continue
        sl = slug(name)
        n4 = sum(1 for x in ss if x['lvl']=='4-year'); n2 = sum(1 for x in ss if x['lvl']=='2-year')
        nA = sum(1 for x in ss if x.get('ad'))
        # one page per school. Same-name campuses exist in the same state (chains of beauty and
        # trade schools especially), so disambiguate by city, then by federal UNITID.
        os.makedirs(f'site/colleges/{sl}', exist_ok=True)
        taken = set()
        for s in ss:
            base = slug(s['n'])
            cand = base
            if cand in taken: cand = f"{base}-{slug(s['c'])}"
            if cand in taken: cand = f"{base}-{s['id']}"
            taken.add(cand)
            s['_slug'] = cand
        body = f"""<h1>Colleges in {name} — all {len(ss)} schools</h1>
<p class="sub">{n4} four-year colleges, {n2} community colleges, and {nA} NCAA/NAIA athletic programs in {name}, with official tuition and average net cost from US Department of Education data.</p>
<a class="cta" href="/app/">Open the interactive map →</a>
{school_rows(ss, state_slug=sl)}
<p style="margin-top:18px">Compare these schools side-by-side, filter by sport and division, and plan campus visits with the free <a href="/app/">My University View map</a>.</p>"""
        open(f'site/colleges/{sl}.html','w').write(page(
            f'Colleges in {name} — Full List with Costs & Athletics ({len(ss)} Schools)',
            f'Every college in {name}: {n4} four-year schools, {n2} community colleges, tuition and real net costs, NCAA & NAIA athletics. Free interactive map.',
            f'{DOMAIN}/colleges/{sl}.html', body))
        state_links.append((name, sl, len(ss)))
        urls.append(f'{DOMAIN}/colleges/{sl}.html')

        big = sorted(ss, key=lambda x: -(x.get('en') or 0))
        for s in ss:
            peers = [p for p in big if p['id'] != s['id']][:8]
            open(f'site/colleges/{sl}/{s["_slug"]}.html','w').write(school_page(s, db, name, sl, peers))
            urls.append(f'{DOMAIN}/colleges/{sl}/{s["_slug"]}.html')
            n_school[0] += 1

    # division pages
    for div,(sl,label) in DIVS.items():
        ss = sorted([s for s in schools if s.get('ad')==div], key=lambda x:(x['s'],x['n']))
        secs = []
        cur = None
        for s in ss:
            if s['s']!=cur:
                if cur is not None: secs.append('</table>')
                cur = s['s']
                secs.append(f'<h2>{STATE_NAMES.get(cur,cur)}</h2><table><tr><th>School</th><th>City</th><th>Tuition (in-state)</th><th>Avg net cost</th></tr>')
            nm = f'<a href="{href(s)}" rel="noopener nofollow">{H.escape(s["n"])}</a>' if s.get('url') else H.escape(s['n'])
            secs.append(f'<tr><td>{nm}</td><td>{H.escape(s["c"])}</td><td>{money(s.get("tin"))}</td><td>{money(s.get("np"))}</td></tr>')
        if ss: secs.append('</table>')
        body = f"""<h1>{label} colleges — all {len(ss)} schools by state</h1>
<p class="sub">Every {label} member school with location, published tuition, and the average net cost families actually pay. For recruiting research: filter by sport on the interactive map to see coaches, conferences, and recruiting links.</p>
<a class="cta" href="/app/">Open the interactive map →</a>
{''.join(secs)}"""
        open(f'site/colleges/{sl}.html','w').write(page(
            f'{label} Colleges — Complete List by State ({len(ss)} Schools) with Costs',
            f'All {len(ss)} {label} colleges listed by state with tuition and average net cost. Filter by sport, see coaches and conferences on the free map.',
            f'{DOMAIN}/colleges/{sl}.html', body))
        urls.append(f'{DOMAIN}/colleges/{sl}.html')

    # hub
    links = '\n'.join(f'<a href="/colleges/{sl}.html">{name} ({n})</a>' for name,sl,n in sorted(state_links))
    divlinks = ' · '.join(f'<a href="/colleges/{sl}.html">{label}</a>' for d,(sl,label) in DIVS.items())
    body = f"""<h1>Browse all 5,777 US colleges by state</h1>
<p class="sub">Full listings with official tuition, real average net costs, and NCAA/NAIA athletics — from US Department of Education data. Or use the <a href="/app/">interactive map</a> to filter by sport, division, cost, and acceptance rate.</p>
<h2>By athletic association</h2><p>{divlinks}</p>
<h2>By state</h2>
<div class="grid">{links}</div>"""
    open('site/colleges/index.html','w').write(page(
        'US Colleges by State — Complete Lists with Costs & Athletics | My University View',
        'Browse all 5,777 US colleges by state or NCAA/NAIA division: tuition, average net cost, community colleges, athletics.',
        f'{DOMAIN}/colleges/', body))

    open('site/robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
    open('site/sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        '\n'.join(f'  <url><loc>{u}</loc></url>' for u in urls) + '\n</urlset>\n')

    print(f'site/ built: {len(state_links)} state pages, {n_school[0]} school pages, 4 division pages,')
    print(f'             hub, sitemap ({len(urls)} urls), robots.txt, index.html, db.js, careers.js, programs.js')

if __name__ == '__main__':
    main()

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

# State pages answer "colleges in X". These answer the two searches it doesn't:
# "community colleges in X" and "trade schools in X". Keyed by the lvl value in db.json.
STATE_TYPES = {
 '2-year': ('community-colleges', 'Community colleges',
            'Community Colleges in {name} — All {n}, with Tuition and Net Cost',
            '{n} two-year public and private colleges in {name}, with published tuition, '
            'average net price after aid, enrollment and transfer-level programs.'),
 'Certificate/trade': ('trade-schools', 'Trade and technical schools',
            'Trade Schools in {name} — All {n} Certificate and Technical Programs',
            '{n} trade, technical and certificate schools in {name}, with published tuition '
            'and average net price after aid — the same federal data as the universities.'),
}

# ---------- career pages ----------
# Crawlable counterpart to the app's Career search. These target the queries families
# actually type ("how to become an electrician", "welder salary") rather than college
# names, which have far less search volume.
#
# PAYWALL: the app sells the per-career list of SCHOOLS (programs.js, Premium). These
# public pages therefore publish the career facts and the programs that lead to the job,
# plus HOW MANY schools offer each — never the school list itself. The count is the hook;
# the names are behind the CTA into /app/.
SOC_GROUPS = {'11':'Management','13':'Business & finance','15':'Computers & IT',
 '17':'Engineering & architecture','19':'Science','21':'Community & social service',
 '23':'Legal','25':'Education','27':'Arts, design, media & film','29':'Healthcare (clinical)',
 '31':'Healthcare support','33':'Protective service','35':'Food & culinary','37':'Building & grounds',
 '39':'Personal care & beauty','41':'Sales','43':'Office & admin','45':'Farming & forestry',
 '47':'Construction trades','49':'Repair & mechanics','51':'Production & manufacturing','53':'Transportation'}
CAR_PATHS = {
 'cert':('Certificate',      'A certificate or short program is the usual way in.'),
 'appr':('Apprenticeship',   'Usually learned through a paid apprenticeship: you earn a wage while you train.'),
 'ojt' :('On the job',       'Most people are hired and trained on the job, so school is optional. A program can still help you stand out.'),
 'deg' :('Degree',           'A degree is the usual way in.'),
 'degx':('Degree + experience','Not an entry-level job: it usually takes a degree plus years of related work.')}

def career_singular(t):
    """'Electricians' -> 'an electrician'. Returns None when the title can't be made
    singular cleanly — BLS titles like 'Welders, cutters, solderers, and brazers' are
    lists, and naively stripping the final 's' produces nonsense."""
    if ',' in t or ' and ' in t.lower(): return None
    low = t.lower()
    if not low.endswith('s') or low.endswith('ss'): return None
    one = low[:-3] + 'y' if low.endswith('ies') else low[:-1]
    return ('an ' if one[0] in 'aeiou' else 'a ') + one

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
dl.faq dt{font-weight:700;margin-top:14px}dl.faq dd{color:var(--dim);margin-top:3px}
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

# Career pages are built from BLS and the NCES crosswalk, not from Scorecard and the
# athletics files, so they get their own source line rather than crediting the wrong data.
FOOT_EDU = ('Data: US Dept. of Education College Scorecard / IPEDS (2022–23) · '
            'Athletics from NCAA/NCSA public listings · Always verify with each college')
FOOT_CAREER = ('Data: US Bureau of Labor Statistics Employment Projections 2025–35 · '
               'NCES CIP–SOC crosswalk · IPEDS completions (2022–23) · Figures are national averages')

def page(title, desc, canonical, body, foot=None):
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
<footer>{foot or FOOT_EDU} ·
<a href="/app/">Interactive map</a> · <a href="/colleges/">All states</a> · <a href="/careers/">Careers</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a> · © Sean Brady</footer>
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
        out.append(f'<tr><td>{nm}</td><td>{H.escape(s["c"])}</td><td>{s["ctrl"]} · {s["lvl"]}</td><td>{dash(s.get("tin"))}</td><td>{dash(s.get("np"))}</td>%s</tr>' % (f'<td>{ath}</td>' if show_div else ''))
    out.append('</table>')
    return '\n'.join(out)


def money(v): return f'${v:,}' if isinstance(v,(int,float)) and v else None

# money() returns None on purpose: the school-page cost table uses `if val:` to drop
# rows it has no figure for. List tables need something visible instead, hence dash().
def dash(v): return money(v) or '—'


def sub_faq(sub, h1, name, sl, seg=None):
    """Answers for a state x type page, from the schools on that page.

    For community colleges the figures are taken over PUBLIC institutions only.
    Federally, a two-year seminary is a 2-year school, and it was turning up as
    'the cheapest community college in New Jersey' — true to the data, and useless
    as an answer, because nobody asking that question means a yeshiva."""
    pool = sub
    low = h1.lower()
    if seg == 'community-colleges':
        pub = [x for x in sub if x.get('ctrl') == 'Public']
        if len(pub) >= 3:
            pool, low = pub, 'public community colleges'
    priced = sorted([x for x in pool if x.get('np')], key=lambda x: x['np'])
    out = []
    out.append((f'How many {h1.lower()} are there in {name}?',
                f'{len(sub)} — every one of them is listed above, from US Department of '
                f'Education data.'))
    if priced:
        c = priced[0]
        link = f'<a href="/colleges/{sl}/{c.get("_slug") or slug(c["n"])}.html">{H.escape(c["n"])}</a>'
        out.append((f'What is the cheapest of the {low} in {name}?',
                    f'By average net price — what students actually pay after grants and '
                    f'scholarships — {link} in {H.escape(c["c"])} is lowest at '
                    f'{money(c["np"])} a year. That is an average across all students, not a '
                    f'quote: your own price depends on your family finances and your record.'))
        mid = priced[len(priced)//2]
        out.append((f'What do {low} cost in {name}?',
                    f'The middle of the range is about {money(mid["np"])} a year after aid, '
                    f'from {money(priced[0]["np"])} to {money(priced[-1]["np"])}. '
                    f'Published tuition is higher — the figures above are what students paid.'))
    return out


# Rough schooling time by federal education level. Deliberately phrased as ranges:
# the federal file says what credential people hold, not how long each person took.
EDU_YEARS = {
 'No formal educational credential': 'no schooling after high school',
 'High school diploma or equivalent': 'no schooling after high school',
 'Postsecondary nondegree award': 'a few months to two years for the certificate',
 'Some college, no degree': 'a year or so of college',
 "Associate's degree": 'about two years for the degree',
 "Bachelor's degree": 'about four years for the degree',
 "Master's degree": 'about six years of study in total',
 'Doctoral or professional degree': 'eight years or more of study',
}
OJT_TIME = {
 'Apprenticeship': 'a paid apprenticeship, usually three to five years',
 'Long-term on-the-job training': 'more than a year of training on the job',
 'Moderate-term on-the-job training': 'a few months to a year of training on the job',
 'Short-term on-the-job training': 'a few weeks of training on the job',
 'Internship/residency': 'an internship or residency, often one to three years',
}

def career_faq(k, cj, one, nschools):
    name = (one.split(' ',1)[1] if one else k['t'].lower())
    ed, ex, oj = cj['edu'][k['e']], cj['exp'][k['x']], cj['ojt'][k['j']]
    out = []
    parts = [EDU_YEARS.get(ed)]
    if oj in OJT_TIME: parts.append(OJT_TIME[oj])
    if ex and ex not in ('None','—'): parts.append(f'{ex.lower()} of related work first')
    parts = [x for x in parts if x]
    if parts:
        out.append((f'How long does it take to become {one}?' if one
                    else 'How long does the training take?',
                    'Typically ' + ', then '.join(parts) + '. That is the usual route rather '
                    'than a rule — people arrive by other paths all the time.'))
    if k.get('w'):
        out.append((f'How much do {k["t"].lower()} make?',
                    f'The US median is {money(k["w"])} a year, meaning half earn more and half '
                    f'less. Pay varies widely by state, employer and experience.'))
    need = {'deg':'Yes — a degree is the usual way in.',
            'degx':'Yes, and employers also expect years of related experience first.',
            'cert':'Not a full degree. A certificate or short programme is the usual route.',
            'appr':'No. Most people train through a paid apprenticeship and earn while they learn.',
            'ojt':'No. Most people are hired and trained on the job; a programme is optional.'}
    out.append((f'Do you need a degree to become {one}?' if one
                else 'Do you need a degree for this work?', need.get(k['p'])))
    if nschools:
        out.append((f'Where can you train to become {one}?' if one
                    else 'Where can you train for this work?',
                    f'{nschools:,} US colleges, community colleges and trade schools award '
                    f'credentials in a matching programme. '
                    f'<a href="/app/">See which ones →</a>'))
    return out


def faq_block(pairs):
    """Short Q&A built from our own figures. The questions are the ones Google's
    "People also ask" actually shows for these searches — cheapest, how many, how long —
    rather than questions we imagined. Emitted as FAQPage data too."""
    pairs = [(q, a) for q, a in pairs if a]
    if not pairs: return ''
    html_q = ''.join(f'<dt>{q}</dt><dd>{a}</dd>' for q, a in pairs)
    ld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":re.sub('<[^>]+>','',q),
         "acceptedAnswer":{"@type":"Answer","text":re.sub('<[^>]+>','',a)}} for q, a in pairs]}
    return (f'<h2>Common questions</h2><dl class="faq">{html_q}</dl>'
            f'<script type="application/ld+json">{json.dumps(ld)}</script>')

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
<h1>{nm}: tuition, cost and admissions</h1>
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
    # Lead the title with the words people actually type — "tuition", "cost",
    # "acceptance rate" — rather than the categories we happen to organise by.
    # Acceptance rate only goes in when the school reports one; open-admission
    # schools get the program angle instead, which is what their searchers want.
    bits = ['Tuition', 'Cost']
    if isinstance(s.get('adm'), (int, float)): bits.append('Acceptance Rate')
    else: bits.append('Programs')
    title = f"{s['n']} — {', '.join(bits)} ({s['c']}, {st})"
    return page(title, desc[:300], f'{DOMAIN}/colleges/{state_slug}/{s.get("_slug") or slug(s["n"])}.html', body)


def career_page(k, cj, peers):
    """One occupation. k is a careers.json record; peers are other careers in the same field."""
    E, X, J = cj['edu'], cj['exp'], cj['ojt']
    nm   = H.escape(k['t'])
    grp  = SOC_GROUPS.get(k['soc'][:2], '')
    lbl, note = CAR_PATHS[k['p']]
    pay  = money(k.get('w'))
    grow = (f"+{k['g']}%" if (k.get('g') or 0) > 0 else f"{k['g']}%") if k.get('g') is not None else '—'
    opens = f"{round(k['o']*1000):,}" if k.get('o') is not None else '—'

    # How you get there, as ordered steps rather than a table of codes.
    steps = []
    ed = E[k['e']]
    steps.append(f'{ed} (a program is optional for this job)' if k['p'] == 'ojt' else ed)
    ex = X[k['x']] if k.get('x') is not None else None
    if ex and ex not in ('None', '—'): steps.append(f'{ex} of experience in a related job')
    oj = J[k['j']] if k.get('j') is not None else None
    if oj and oj not in ('None', '—'): steps.append(oj)
    one = career_singular(k['t'])
    steps.append(f'Work as {one}' if one else f'Work in: {k["t"].lower()}')
    steps_html = ''.join(f'<li>{H.escape(s)}</li>' for s in steps)

    # Programs that lead here. Schools-per-program is a COUNT only; the list is Premium.
    rows = []
    for cip in k.get('c', []):
        info = cj['cips'].get(cip)
        if not info: continue
        rows.append((info[0], info[1] or 0, cip))
    rows.sort(key=lambda r: -r[1])
    if rows:
        prog_rows = ''.join(
            f'<tr><td>{H.escape(t)}</td><td>CIP {H.escape(c)}</td>'
            f'<td style="text-align:right">{n:,}</td></tr>' for t, n, c in rows[:25])
        extra = f'<p class="note">…and {len(rows)-25} more related programs.</p>' if len(rows) > 25 else ''
        programs = f"""<h2>Programs that lead to this job</h2>
<p>These are the federal program codes (CIP) that the Department of Education maps to this
occupation, and how many US colleges, community colleges or trade schools report awarding
credentials in each.</p>
<table><tr><th>Program</th><th>Code</th><th style="text-align:right">Schools</th></tr>{prog_rows}</table>{extra}"""
    else:
        programs = """<h2>Programs that lead to this job</h2>
<p>No specific college program maps to this occupation in the federal crosswalk — people
usually arrive here through experience, training on the job, or a related field rather
than a dedicated course of study.</p>"""

    nschools = k.get('n') or 0
    cta = (f'<p><a class="cta" href="/app/">See the {nschools:,} schools that offer these programs →</a></p>'
           if nschools else '<p><a class="cta" href="/app/">Explore schools on the map →</a></p>')

    rel = ' · '.join(f'<a href="/careers/{slug(p["t"])}.html">{H.escape(p["t"])}</a>' for p in peers)
    related = f'<h2>Related careers in {H.escape(grp)}</h2><p>{rel}</p>' if rel else ''

    ld = {"@context": "https://schema.org", "@type": "Occupation", "name": k['t'],
          "occupationalCategory": k['soc'],
          "description": f"{k['t']}: median US pay {pay}, {grow} projected growth 2025–35.",
          "estimatedSalary": {"@type": "MonetaryAmountDistribution", "name": "base",
                              "currency": "USD", "median": k.get('w')} if k.get('w') else None}
    ld = {x: y for x, y in ld.items() if y is not None}

    h1 = (f'How to become {one}' if one
          else f'{nm}: pay, training and the programs that lead there')
    body = f"""<div class="crumb"><a href="/">Home</a> › <a href="/careers/">Careers</a> › {nm}</div>
<h1>{h1}</h1>
<p class="sub">{H.escape(grp)} · SOC {H.escape(k['soc'])}</p>
<div class="facts">
  <div class="fact"><b>{pay}</b><span>US median pay, 2025</span></div>
  <div class="fact"><b>{grow}</b><span>Projected growth, 2025–35</span></div>
  <div class="fact"><b>{opens}</b><span>Openings per year</span></div>
  <div class="fact"><b>{H.escape(lbl)}</b><span>Usual way in</span></div>
</div>
<h2>How you get in</h2>
<p>{H.escape(note)}</p>
<ol>{steps_html}</ol>
{programs}
{cta}
{faq_block(career_faq(k, cj, one, nschools))}
<p class="note"><b>Pay and growth are national figures.</b> What you earn depends on where you work,
your employer and your experience, and these are projections rather than promises. Education
requirements describe how most people enter the job, not a rule — plenty of people take another route.<br><br>
Pay, growth, openings and entry requirements: <b>US Bureau of Labor Statistics</b>, Employment
Projections 2025–35. Program-to-occupation mapping: <b>NCES CIP–SOC crosswalk</b> (2020/2018).
School counts: <b>IPEDS completions</b>, 2022–23.</p>
{related}
<script type="application/ld+json">{json.dumps(ld)}</script>"""
    # The title is a stronger signal than the H1, so it gets the phrase people type.
    # "How to become an electrician" is a real query; "Electricians" barely is.
    if one:
        art, _, rest = one.partition(' ')      # "an electrician" -> "an" + "electrician"
        title = f"How to Become {art} {rest.title()} — Pay, Training and Programs"
    else:
        title = f"{k['t']} — Pay, Job Growth and Training"
    desc = (f"{k['t']}: median US pay {pay}, {grow} projected growth to 2035, about {opens} openings a year. "
            f"{lbl} is the usual way in. See the programs and schools that train for it.")
    return page(title, desc[:300], f'{DOMAIN}/careers/{slug(k["t"])}.html', body, foot=FOOT_CAREER)


def build_careers(cj):
    """Writes /careers/ hub + one page per occupation that has programs mapped to it.
    Occupations with no CIP mapping are skipped: their pages would be near-empty, and
    thin templated pages at scale are exactly what search engines penalise."""
    os.makedirs('site/careers', exist_ok=True)
    have = [k for k in cj['careers'] if k.get('c')]
    by_group = {}
    for k in have:
        by_group.setdefault(k['soc'][:2], []).append(k)
    for g in by_group:
        by_group[g].sort(key=lambda k: -(k.get('o') or 0))

    urls = []
    for k in have:
        peers = [p for p in by_group[k['soc'][:2]] if p['soc'] != k['soc']][:8]
        open(f'site/careers/{slug(k["t"])}.html', 'w').write(career_page(k, cj, peers))
        urls.append(f'{DOMAIN}/careers/{slug(k["t"])}.html')

    secs = []
    for g, name in SOC_GROUPS.items():
        ks = by_group.get(g)
        if not ks: continue
        links = ' · '.join(
            f'<a href="/careers/{slug(k["t"])}.html">{H.escape(k["t"])}</a>' for k in ks)
        secs.append(f'<h2>{H.escape(name)}</h2><p class="sub">{len(ks)} careers</p><p>{links}</p>')
    hub = f"""<div class="crumb"><a href="/">Home</a> › Careers</div>
<h1>Search by career, not by major</h1>
<p class="sub">{len(have)} careers, with what they pay, how fast they are growing, how many
openings there are each year, and which college programs lead to them. Federal data — BLS
Employment Projections and the Department of Education's program–occupation crosswalk.</p>
<p><a class="cta" href="/app/">Open the career search →</a></p>
{''.join(secs)}"""
    open('site/careers/index.html', 'w').write(page(
        'Careers — Pay, Growth and the College Programs That Lead There',
        f'{len(have)} careers with median pay, projected growth to 2035, annual openings and the '
        'college and trade-school programs that train for each. Free, from federal data.',
        f'{DOMAIN}/careers/', hub, foot=FOOT_CAREER))
    return [f'{DOMAIN}/careers/'] + urls


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

    # Career search data (built by build_careers.py). careers.js is the small career index every
    # visitor loads; programs.js (school x program lists) is only fetched once Premium is active.
    career_urls, career_nav = [], ''
    if os.path.exists('careers.json'):
        cj = json.load(open('careers.json'))
        progs = cj.pop('programs')
        open('site/careers.js','w').write('window.__CAREERS=' + json.dumps(cj, separators=(',',':')) + ';')
        open('site/programs.js','w').write('window.__PROGRAMS=' + json.dumps(progs, separators=(',',':')) + ';')
        career_urls = build_careers(cj)
        # Homepage teaser. NOT sorted by openings: that surfaces home health aides, office
        # clerks and cooks — the highest-volume jobs in America, but mostly ones needing no
        # college, which is a poor advertisement on a college-search homepage. This is a
        # curated spread of trades, healthcare, tech and creative work that people actually
        # search for by name, mirroring the app's own popular list.
        WANT = ['Electricians', 'Registered nurses', 'Welders', 'Software developers',
                'Plumbers', 'Dental hygienists', 'Heating, air conditioning',
                'Automotive service technicians', 'Paralegals', 'Graphic designers',
                'Radiologic technologists', 'Carpenters', 'Accountants',
                'Aircraft mechanics', 'Veterinary technologists', 'Police and sheriff']
        have = {k['t']: k for k in cj['careers'] if k.get('c')}
        picked, seen = [], set()
        for want in WANT:
            hit = next((k for t, k in have.items()
                        if t.lower().startswith(want.lower()) and t not in seen), None)
            if hit:
                picked.append(hit); seen.add(hit['t'])
        career_nav = ' · '.join(
            f'<a href="/careers/{slug(k["t"])}.html">{H.escape(k["t"])}</a>' for k in picked)
        career_nav += ' · <a href="/careers/">All careers</a>'
    else:
        print('WARN careers.json missing — run build_careers.py; Career search will show an error')

    home = open('homepage.html').read()
    home = home.replace('<!--ANALYTICS-->', ANALYTICS)
    home = home.replace('<!--STATELINKS-->', state_nav)
    home = home.replace('<!--CAREERLINKS-->', career_nav)
    for ph in ('<!--STATELINKS-->', '<!--CAREERLINKS-->'):
        assert ph not in home, f'placeholder not substituted: {ph}'
    open('site/index.html','w').write(home)

    open('site/db.js','w').write('window.__DBDATA=' + json.dumps(db, separators=(',',':')) + ';')

    n_school=[0]; n_type=[0]; type_links={}
    urls = [f'{DOMAIN}/', f'{DOMAIN}/app/', f'{DOMAIN}/colleges/'] + career_urls
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
        subs = [(seg, h1, len([x for x in ss if x['lvl']==lvl]))
                for lvl, (seg, h1, _t, _b) in STATE_TYPES.items()
                if len([x for x in ss if x['lvl']==lvl]) >= 5]
        sublinks = (' · '.join(f'<a href="/colleges/{sl}-{seg}.html">{h1} in {name} ({n})</a>'
                               for seg, h1, n in subs))
        subrow = f'<p class="sub" style="margin-top:10px">Narrow it down: {sublinks}</p>' if subs else ''
        body = f"""<h1>Colleges in {name} — all {len(ss)} schools</h1>
<p class="sub">{n4} four-year colleges, {n2} community colleges, and {nA} NCAA/NAIA athletic programs in {name}, with official tuition and average net cost from US Department of Education data.</p>
{subrow}
<a class="cta" href="/app/">Open the interactive map →</a>
{school_rows(ss, state_slug=sl)}
<p style="margin-top:18px">Compare these schools side-by-side, filter by sport and division, and plan campus visits with the free <a href="/app/">My University View map</a>.</p>"""
        open(f'site/colleges/{sl}.html','w').write(page(
            f'Colleges in {name} — Full List with Costs & Athletics ({len(ss)} Schools)',
            f'Every college in {name}: {n4} four-year schools, {n2} community colleges, tuition and real net costs, NCAA & NAIA athletics. Free interactive map.',
            f'{DOMAIN}/colleges/{sl}.html', body))
        state_links.append((name, sl, len(ss)))
        urls.append(f'{DOMAIN}/colleges/{sl}.html')

        # "community colleges in X" and "trade schools in X" are their own searches,
        # distinct from "colleges in X", and the state page above answers none of them
        # directly. Only built where there are enough schools to be worth a page —
        # a list of two is thin content and better left on the main state page.
        for lvl, (seg, h1, ttl, blurb) in STATE_TYPES.items():
            sub = [x for x in ss if x['lvl'] == lvl]
            if len(sub) < 5: continue
            sb = f"""<div class="crumb"><a href="/">Home</a> › <a href="/colleges/">Colleges</a> › <a href="/colleges/{sl}.html">{name}</a> › {h1}</div>
<h1>{h1} in {name} — all {len(sub)}</h1>
<p class="sub">{blurb.format(name=name, n=len(sub))}</p>
<a class="cta" href="/app/">Open the interactive map →</a>
{school_rows(sub, state_slug=sl)}
{faq_block(sub_faq(sub, h1, name, sl, seg))}
<p style="margin-top:18px">See every school in {name} on the <a href="/colleges/{sl}.html">full {name} list</a>,
or compare costs side by side on the free <a href="/app/">My University View map</a>.</p>"""
            open(f'site/colleges/{sl}-{seg}.html','w').write(page(
                ttl.format(name=name, n=len(sub)),
                f'All {len(sub)} {h1.lower()} in {name}, with published tuition, average net price after aid, '
                f'enrollment and programs. Federal data, free to search.',
                f'{DOMAIN}/colleges/{sl}-{seg}.html', sb))
            urls.append(f'{DOMAIN}/colleges/{sl}-{seg}.html')
            n_type[0] += 1
            type_links.setdefault(seg, []).append((name, f'{sl}-{seg}', len(sub)))

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
            secs.append(f'<tr><td>{nm}</td><td>{H.escape(s["c"])}</td><td>{dash(s.get("tin"))}</td><td>{dash(s.get("np"))}</td></tr>')
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
    print(f'             hub, {len(career_urls)-1 if career_urls else 0} career pages,\n             sitemap ({len(urls)} urls), robots.txt, index.html, db.js, careers.js, programs.js')

if __name__ == '__main__':
    main()

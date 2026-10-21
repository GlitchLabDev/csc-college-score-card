# build_careers.py — builds careers.json (career search data) from federal files in raw/.
#   python3 build_careers.py
# Inputs (download into src/raw/, gitignored):
#   C2023_A.zip  -> C2023_a_RV.csv   IPEDS 2022-23 completions: awards by school x 6-digit CIP x award level
#   CIP2020_SOC2018_Crosswalk.xlsx   NCES/BLS crosswalk: which programs lead to which occupations
#   occupation.xlsx                  BLS Employment Projections, Table 1.2: pay, growth, education, experience
# Output: careers.json — read by build_site.py, which writes site/careers.js and site/programs.js.
import csv, json, os, re, openpyxl
from collections import defaultdict

RAW = 'raw'
db = json.load(open('db.json'))
idx_of = {s['id']: i for i, s in enumerate(db['schools'])}

# ---- BLS occupations ----
wb = openpyxl.load_workbook(os.path.join(RAW, 'occupation.xlsx'), read_only=True)
rows = list(wb['Table 1.2'].iter_rows(values_only=True))
hdr = rows[1]
col = {h: i for i, h in enumerate(hdr) if h}
def c(r, name): return r[col[name]]
EDU, EXP, OJT = [], [], []
def code(lst, v):
    v = (v or '').strip()
    if v not in lst: lst.append(v)
    return lst.index(v)
occ = {}
for r in rows[2:]:
    if not r or not r[1] or c(r, 'Occupation type') != 'Line item': continue
    soc = r[1].strip()
    wage = c(r, 'Median annual wage, dollars, 2025')
    occ[soc] = dict(
        soc=soc, t=r[0].strip(),
        w=wage if isinstance(wage, (int, float)) else None,   # '>=239,200' style strings -> None
        wt=wage if isinstance(wage, str) and wage.strip() not in ('', '—') else None,
        g=c(r, 'Employment change, percent, 2025–35'),
        o=c(r, 'Occupational openings, 2025–35 annual average'),
        e=code(EDU, c(r, 'Typical education needed for entry')),
        x=code(EXP, c(r, 'Work experience in a related occupation')),
        j=code(OJT, c(r, 'Typical on-the-job training needed to attain competency in the occupation')),
    )
print(len(occ), 'BLS occupations')

def path_type(o):
    e, x, j = EDU[o['e']], EXP[o['x']], OJT[o['j']]
    if 'Apprenticeship' in j: return 'appr'
    if e in ('No formal educational credential', 'High school diploma or equivalent'): return 'ojt'
    if e in ('Postsecondary nondegree award', 'Some college, no degree'): return 'cert'
    return 'degx' if x and x != 'None' else 'deg'

# ---- crosswalk SOC -> CIP ----
wb = openpyxl.load_workbook(os.path.join(RAW, 'CIP2020_SOC2018_Crosswalk.xlsx'), read_only=True)
soc_cips = defaultdict(set); cip_title = {}
for r in list(wb['SOC-CIP'].iter_rows(values_only=True))[1:]:
    if not r or not r[0] or r[2] in (None, '99.9999'): continue
    soc_cips[r[0].strip()].add(r[2].strip()); cip_title[r[2].strip()] = r[3].strip().rstrip('.')
def cips_for(soc):
    if soc in soc_cips: return soc_cips[soc]
    # BLS sometimes reports an aggregate (e.g. 29-2040 for EMTs + paramedics): match its children
    if soc.endswith('0'):
        stem = soc[:-1]
        out = set()
        for k, v in soc_cips.items():
            if k.startswith(stem): out |= v
        return out
    return set()

# ---- completions ----
LEVEL_BIT = {'20': 1, '21': 1, '1': 1, '2': 2, '4': 2, '3': 4, '5': 8,
             '6': 16, '7': 16, '8': 16, '17': 16, '18': 16, '19': 16}
prog = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # cip -> school idx -> [mask, grads]
with open(os.path.join(RAW, 'C2023_a_RV.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['MAJORNUM'] != '1': continue
        cip = r['CIPCODE'].strip('"')
        if len(cip) != 7: continue          # skip 2-digit totals and 99
        i = idx_of.get(int(r['UNITID']))
        b = LEVEL_BIT.get(r['AWLEVEL'])
        if i is None or not b: continue
        n = int(r['CTOTALT'] or 0)
        if n <= 0: continue
        e = prog[cip][i]; e[0] |= b; e[1] += n

# ---- curated search aliases (plain words people type) ----
ALIASES = {
 '51-4121':'welder welding fabricator', '49-3023':'auto mechanic car mechanic automotive technician',
 '49-3031':'diesel mechanic diesel technician truck mechanic', '47-2111':'electrician electrical wireman',
 '49-9051':'lineman lineworker power line', '49-9021':'hvac technician heating air conditioning refrigeration',
 '47-2152':'plumber pipefitter steamfitter', '47-2031':'carpenter framer', '31-9092':'medical assistant',
 '49-3011':'aircraft mechanic a&p aviation mechanic airplane mechanic', '35-1011':'chef head cook',
 '39-5012':'cosmetologist hair stylist hairdresser beautician', '39-5011':'barber',
 '13-1082':'project manager pm it project manager technology project manager program manager scrum master',
 '11-3021':'it manager it director technology manager cio', '15-1252':'software engineer programmer coder developer app developer',
 '15-1212':'cybersecurity cyber security analyst', '15-1232':'help desk it support tech support',
 '15-1244':'network administrator sysadmin', '29-1141':'nurse rn registered nurse', '29-2061':'lpn lvn practical nurse',
 '31-1131':'cna nursing assistant', '29-2042':'emt emergency medical technician ambulance', '29-2043':'paramedic', '29-1292':'dental hygienist',
 '31-9091':'dental assistant', '29-2052':'pharmacy technician pharmacy tech', '29-2034':'x-ray tech radiology tech',
 '31-2021':'physical therapist assistant pta', '29-1123':'physical therapist pt', '33-3051':'police officer cop sheriff',
 '33-2011':'firefighter fireman', '53-3032':'truck driver cdl trucker', '53-2011':'pilot airline pilot',
 '47-2073':'heavy equipment operator operating engineer', '49-9071':'maintenance technician handyman',
 '51-4041':'machinist cnc', '47-2181':'roofer', '47-2141':'painter', '47-2221':'ironworker',
 '47-2021':'mason bricklayer', '47-4021':'elevator mechanic', '47-2231':'solar installer',
 '49-9081':'wind turbine technician', '23-2011':'paralegal legal assistant', '23-1011':'lawyer attorney',
 '13-2011':'accountant cpa auditor', '25-2021':'teacher elementary teacher', '27-1024':'graphic designer',
 '27-4031':'camera operator cinematographer', '27-4032':'video editor film editor',
 '27-2012':'film producer director tv producer production assistant', '27-4099':'key grip grip gaffer',
 '27-4011':'sound technician audio engineer av technician', '11-9021':'construction manager construction project manager',
 '13-1051':'estimator cost estimator', '17-2051':'civil engineer', '17-1011':'architect',
 '35-2014':'line cook cook', '39-9011':'childcare daycare', '31-9011':'massage therapist',
 '29-1131':'veterinarian vet', '29-2056':'vet tech veterinary technician', '41-9022':'realtor real estate agent',
 '15-2051':'data scientist', '13-1111':'business analyst consultant management analyst',
}

careers = []
missing = [s for s in ALIASES if s not in occ]
if missing: print('WARN alias SOCs not in BLS file:', missing)
for soc, o in sorted(occ.items()):
    cs = sorted(cips_for(soc))
    if soc.startswith('25-1'): continue                       # postsecondary teachers: every CIP, not useful
    reach = set()
    for cp in cs: reach |= set(prog.get(cp, {}).keys())
    o2 = dict(o); o2['p'] = path_type(o); o2['c'] = cs; o2['n'] = len(reach)
    if soc in ALIASES: o2['a'] = ALIASES[soc]
    if o2['wt'] is None: o2.pop('wt')
    careers.append(o2)

used = sorted({cp for k in careers for cp in k['c'] if cp in prog})
programs = {}
for cp in used:
    programs[cp] = ';'.join(f'{i}:{m}:{n}' for i, (m, n) in sorted(prog[cp].items()))
out = dict(source='BLS Employment Projections 2025–35 · NCES CIP–SOC crosswalk 2020/2018 · IPEDS completions 2022–23',
           edu=EDU, exp=EXP, ojt=OJT, careers=careers,
           cips={cp: [cip_title.get(cp, cp), len(prog.get(cp, {}))] for cp in sorted({cp for k in careers for cp in k['c']})},
           programs=programs)
json.dump(out, open('careers.json', 'w'), separators=(',', ':'))
from collections import Counter
print(len(careers), 'careers ·', Counter(k['p'] for k in careers))
print('no programs:', sum(1 for k in careers if k['n'] == 0))
print('careers index bytes ~', len(json.dumps({k: out[k] for k in ('edu','exp','ojt','careers','cips')}, separators=(',',':'))))
print('programs bytes ~', len(json.dumps(programs, separators=(',',':'))))
print('EDU', EDU); print('EXP', EXP); print('OJT', OJT)

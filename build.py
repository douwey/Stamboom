"""Stamboom bouwen uit een csv.
Gebruik: python3 build.py csv [uitvoer.html]
Uitgangspunten: de csv klopt. Paren met kinderen vormen een gezin. Partners zonder kinderen komen naast elkaar te staan,
tenzij dat een kind in het gezin van zijn eigen ouders zou zetten: dan wordt het een gestippelde lijn.
De indeling zelf (rijen, kolommen, uitklappen) gebeurt in de pagina (template.html)."""
import csv, os, re, json, sys, collections
sys.setrecursionlimit(10000)
HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    sys.exit("Gebruik: python3 build.py jouw.csv [stamboom.html]")
SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'stamboom.html'
CW, CH, ROW = 124, 64, 150
notes = []

def num(s):
    s = (s or '').strip()
    return int(s) if re.fullmatch(r'\d+', s) else None

# ---------- inlezen
P = {}
rd = csv.DictReader(open(SRC, encoding='utf-8-sig'))
for r in rd:
    r = {(k or '').strip().lower(): (v or '') for k, v in r.items()}
    nm = r.get('naam', '').strip()
    if not nm or not r.get('id', '').strip().isdigit():
        continue
    i = int(r['id'])
    P[i] = dict(id=i, f=num(r.get('vader id')), m=num(r.get('moeder id')),
                pl=[int(x) for x in re.findall(r'\d+', r.get('partner id', ''))],
                name=nm[0].upper() + nm[1:], sex=r.get('mv', '').strip().lower(),
                born=num(r.get('geboren')), died=num(r.get('overleden')), age=num(r.get('leeftijd')),
                comment=r.get('comment', '').strip())
broken = []
for p in P.values():
    for key in ('f', 'm'):
        if p[key] is not None and p[key] not in P:
            broken.append(f"{p['name']} (id {p['id']}) verwijst naar onbekende ouder id {p[key]}"); p[key] = None
if broken: notes.append("Onbekende ouders in de csv, genegeerd: " + "; ".join(broken) + ".")

# geslacht volgt de rol: moeder id => vrouw, vader id => man
mothers = collections.defaultdict(list); fathers = collections.defaultdict(list)
for p in P.values():
    if p['m']: mothers[p['m']].append(p['name'])
    if p['f']: fathers[p['f']].append(p['name'])
for i, p in P.items():
    want = 'v' if i in mothers else 'm' if i in fathers else None
    if want and p['sex'] != want:
        if p['sex'] in ('m', 'v'):
            notes.append(f"{p['name']} heeft in de csv geslacht '{p['sex']}', maar komt voor als {'moeder' if want == 'v' else 'vader'} van {', '.join(mothers[i] if want == 'v' else fathers[i])}. Getoond als {'vrouw' if want == 'v' else 'man'}.")
        p['sex'] = want

# ---------- paren
strong = {frozenset((p['f'], p['m'])) for p in P.values() if p['f'] and p['m'] and p['f'] != p['m']}
pairs = set()
for p in P.values():
    for q in p['pl']:
        if q in P and q != p['id']: pairs.add(frozenset((p['id'], q)))
partners = collections.defaultdict(set)
for l in pairs | strong:
    a, b = tuple(l); partners[a].add(b); partners[b].add(a)
weak = sorted(tuple(sorted(l)) for l in pairs if l not in strong)

par = {i: i for i in P}; mem = {i: {i} for i in P}
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: par[rb] = ra; mem[ra] |= mem.pop(rb)
for l in sorted(tuple(sorted(x)) for x in strong): union(*l)
def conflict(a, b):
    Ma, Mb = mem[find(a)], mem[find(b)]
    for X, Y in ((Ma, Mb), (Mb, Ma)):
        for x in X:
            if P[x]['f'] in Y or P[x]['m'] in Y: return True
    return False
dotted = []
for a, b in weak:
    if find(a) == find(b): continue
    if conflict(a, b): dotted.append((a, b))
    else: union(a, b)
for a, b in dotted:
    notes.append(f"{P[a]['name']} en {P[b]['name']} staan in de csv als partners, maar hebben geen kinderen samen en horen elk al bij een eigen gezin. Ze zijn met een gestippelde lijn verbonden.")
for a, b in sorted(tuple(sorted(x)) for x in strong):
    if P[a]['f'] == b or P[a]['m'] == b: notes.append(f"{P[a]['name']} is in de csv kind en partner van {P[b]['name']} en staat naast {P[b]['name']}.")
    elif P[b]['f'] == a or P[b]['m'] == a: notes.append(f"{P[b]['name']} is in de csv kind en partner van {P[a]['name']} en staat naast {P[a]['name']}.")

# ---------- gezinnen (units)
hasp = lambda x: bool(P[x]['f'] or P[x]['m'])
unit_of, units = {}, {}
for r, members in mem.items():
    members = sorted(members)
    if len(members) == 1: h = members[0]
    else:
        wp = [x for x in members if hasp(x)]
        if len(wp) == 1: h = wp[0]
        else:
            pool = wp or members
            h = min([x for x in pool if P[x]['sex'] == 'm'] or pool)
    order = {q: i for i, q in enumerate(P[h]['pl'])}
    sp = sorted([x for x in members if x != h], key=lambda q: (order.get(q, 1000), q))
    units[h] = dict(m=[h] + sp, par=None, k=[], anchor=0)
    for x in members: unit_of[x] = h
children = collections.defaultdict(list)
for p in P.values():
    for q in (p['f'], p['m']):
        if q: children[q].append(p['id'])

ghost = set()
for h, u in units.items():
    if len(u['m']) == 1 and not hasp(h) and children[h] and all(unit_of[c] != c for c in children[h]):
        ghost.add(h)
heads = [h for h in units if h not in ghost]

pu = {}
for h in heads:
    pu[h] = None
    for q in (P[h]['f'], P[h]['m']):
        if q and unit_of[q] not in ghost and unit_of[q] != h:
            pu[h] = unit_of[q]; break
kids_of = collections.defaultdict(list)
for h in heads:
    if pu[h] is not None: kids_of[pu[h]].append(h)
def root_of(u):
    seen = set()
    while pu[u] is not None and u not in seen: seen.add(u); u = pu[u]
    return u
def tree_size(u, seen=()):
    return sum(1 + tree_size(c, seen + (u,)) for c in kids_of[u] if c not in seen)
roots = sorted([h for h in heads if pu[h] is None], key=lambda r: (-tree_size(r), r))
main = roots[0]

# ---------- takken van aangetrouwde partners aan de hoofdboom hangen
def candidates(R):
    own = {h for h in heads if root_of(h) == R}
    out = []
    def walk(u, d):
        for m in units[u]['m']:
            for c in children[m]:
                if unit_of[c] == c:
                    if c in own and c != u: walk(c, d + 1)
                elif unit_of[c] != u and unit_of[c] not in own and unit_of[c] not in ghost:
                    out.append((d, c, u))
    walk(R, 0)
    return out
atts = []; resolved = {main}; left = roots[1:]
progress = True
while progress:
    progress = False
    for R in list(left):
        cs = [x for x in candidates(R) if root_of(unit_of[x[1]]) in resolved]
        if not cs: continue
        d, c, u = sorted(cs, key=lambda x: (-x[0], x[1]))[0]
        atts.append(dict(spouse=c, host=unit_of[c], parUnit=u, root=R, depth=d))
        others = [x for x in cs if x[1] != c]
        sn = ', '.join(P[x[1]]['name'] for x in others)
        notes.append(f"De stamboom van {P[R]['name']} hangt via {P[c]['name']} aan die van {P[root_of(unit_of[c])]['name']}. {P[c]['name']} staat daarom vooraan in het gezin van {P[unit_of[c]]['name']}, met haar ouder recht erboven. Open de tak met het knopje 'afkomst'." + (f" Andere koppelingen ({sn}) zijn niet getekend: die staan bij hun partner, met de ouder op de kaart." if others else ""))
        resolved.add(R); left.remove(R); progress = True
extra = left
if extra: notes.append("Losse stambomen zonder koppeling aan de hoofdboom, rechts getoond: " + ", ".join(P[r]['name'] for r in extra) + ".")
att_of_root = {a['root']: a for a in atts}

# ---------- generaties
G = {}
def gen(h, stack=()):
    if h in G: return G[h]
    if h in stack: return 0
    if pu[h] is not None: G[h] = gen(pu[h], stack + (h,)) + 1
    elif h in att_of_root:
        a = att_of_root[h]; G[h] = gen(a['host'], stack + (h,)) - 1 - a['depth']
    else: G[h] = 0
    return G[h]
for h in heads: gen(h)
gmin = min(G.values()); G = {h: g - gmin for h, g in G.items()}

for a in atts:
    m = units[a['host']]['m']
    if m[0] != a['spouse']: m.remove(a['spouse']); m.insert(0, a['spouse'])
for h in heads:
    if pu[h] is None: continue
    mm = units[pu[h]]['m']
    a = 0
    if P[h]['m'] in mm: a = mm.index(P[h]['m'])
    elif P[h]['f'] in mm: a = mm.index(P[h]['f'])
    units[h]['par'] = pu[h]; units[h]['anchor'] = a
    units[pu[h]]['k'].append(h)
for u in units.values(): u['k'].sort(key=lambda c: (units[c]['anchor'], c))
for a in atts:   # de lijn naar de afkomst-tak komt als laatste (rechts)
    c = a['parUnit']
    while units[c]['par'] is not None:
        p = units[c]['par']; units[p]['k'].remove(c); units[p]['k'].append(c); c = p

gh = ", ".join(P[h]['name'] for h in sorted(ghost))
if gh: notes.append(f"Deze personen hebben geen eigen blok, omdat ze alleen de vader of moeder van een aangetrouwde partner zijn: {gh}. Hun naam staat op de kaart van hun kind.")
notes.append("Aangetrouwde partners staan op de rij van hun partner. Hun eigen ouder staat soms in een andere tak en is dan alleen als tekst op de kaart vermeld.")

# ---------- personen
def nm(i): return P[i]['name'] if i else None
persons = []
for i, p in P.items():
    if unit_of[i] in ghost: continue
    u = unit_of[i]
    d = (f"{p['born']}–{p['died']}" if p['born'] is not None and p['died'] is not None else
         f"geb. {p['born']}" if p['born'] is not None else f"† {p['died']}" if p['died'] is not None else '')
    l2 = l3 = ''
    if i != u:
        l2 = ('vrouw' if p['sex'] == 'v' else 'man' if p['sex'] == 'm' else 'partner') + ' van ' + nm(u)
        pf = p['f'] or p['m']
        l3 = (('dochter' if p['sex'] == 'v' else 'zoon' if p['sex'] == 'm' else 'kind') + ' van ' + nm(pf)) if pf else (d or p['comment'])
    else:
        miss = [(lab, q) for lab, q in (('vader', p['f']), ('moeder', p['m'])) if q and unit_of[q] != pu[u]]
        l2 = d or (f"{miss[0][0]}: {nm(miss[0][1])}" if miss else p['comment'])
        if d and miss: l3 = f"{miss[0][0]}: {nm(miss[0][1])}"
    persons.append(dict(id=i, n=p['name'], s=p['sex'] if p['sex'] in ('m', 'v') else '', l2=l2, l3=l3, c=p['comment'],
                        b=p['born'], o=p['died'], a=p['age'], f=p['f'], m=p['m'], u=u, pl=sorted(partners[i])))

dn = collections.defaultdict(list)
for a_, b_ in dotted: dn[a_].append(P[b_]['name']); dn[b_].append(P[a_]['name'])
for p in persons:
    if p['id'] in dn:
        txt = 'ook partner: ' + ', '.join(dn[p['id']])
        if not p['l2']: p['l2'] = txt
        elif not p['l3']: p['l3'] = txt
D = dict(cw=CW, ch=CH, rowh=ROW, persons=persons,
         units={str(h): dict(m=units[h]['m'], par=units[h]['par'], k=units[h]['k'], anc=units[h]['anchor'], g=G[h]) for h in heads},
         atts=atts, roots=[main] + [r for r in roots[1:] if r in extra], weak=[list(w) for w in dotted], notes=notes)
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
open(OUT, 'w', encoding='utf-8').write(tpl.replace('/*DATA*/null', json.dumps(D, ensure_ascii=False, separators=(',', ':'))))
print('personen', len(persons), 'van', len(P), '| hoofdboom', P[main]['name'], '| takken gekoppeld', [(P[a['root']]['name'], P[a['spouse']]['name']) for a in atts],
      '| los', [P[r]['name'] for r in extra], '| gestippeld', [(P[a]['name'], P[b]['name']) for a, b in dotted])
for n in notes: print(' -', n)

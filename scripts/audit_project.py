#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, html, json, re, subprocess, sys, tempfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

R=Path(__file__).resolve().parents[1]; E=[]; OK=[]
KNOWN_NAME_DIFF={"9360-0903":("Metody instrumentální analýzy II.","Metody instrumentální analýzy II")}
def bad(x): E.append(x)
def ok(x): OK.append(x)
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def text(p): return p.read_text(encoding='utf-8',errors='replace')
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def block(t,id):
 m=re.search(rf'<table id="{re.escape(id)}".*?</table>',t,re.S); return m.group(0) if m else ''
def rows(b):
 m=re.search(r'<tbody[^>]*>(.*?)</tbody>',b,re.S)
 return [] if not m else [[clean(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)] for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',m.group(1),re.S)]
def val(t,label):
 m=re.search(rf'<td class="label"><span class="outputText">{re.escape(label)}</span></td><td class="value">(?:<span class="outputText">)?(.*?)(?:</span>)?</td>',t,re.S)
 return clean(m.group(1)) if m else ''
def role(t):
 m=re.search(r'<tbody[^>]*>(.*?)</tbody>',block(t,'form1:tableTeachers'),re.S)
 if not m:return ''
 for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',m.group(1),re.S):
  td=re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)
  if len(td)>=4 and clean(td[0])=='PLA88':
   c='selected-green.png' in td[2]; p='selected-green.png' in td[3]
   return 'cvičící + přednášející' if c and p else 'cvičící' if c else 'přednášející' if p else 'uvedena bez označené role'
 return ''
def meta(p):
 t=text(p); fs=rows(block(t,'form1:tableForms'))
 return {'lang':val(t,'Jazyk výuky'),'credits':val(t,'Kredity'),'faculty':val(t,'Určeno pro fakulty'),'study':val(t,'Určeno pro typy studia'),'forms':[' | '.join(x[:3]) for x in fs if x],'role':role(t)}
def page_name(p,ident):
 t=html.unescape(text(p)); m=re.search(rf'<title>\s*{re.escape(ident)}\s+[–-]\s*(.*?)</title>',t,re.S)
 if not m:
  m=re.search(rf'<span class="outputText">\s*{re.escape(ident)}\s+[–-]\s*(.*?)</span>',t,re.S)
 if not m:return ''
 return re.sub(r'\s+\([^()]*\)$','',clean(m.group(1))).strip()
def summary(p): return {c:n.strip() for c,n in re.findall(r'(?m)^(\d{3,4}-\d{4})\t(.+)$',text(p))}
def lang(s):
 s=s.lower(); return 'CZ' if 'češt' in s else 'EN' if 'anglič' in s else s

# Raw archive + manifests
subs=sorted((R/'archive/subjects').glob('subject_*.html')); vers=sorted((R/'archive/versions').glob('version_*.html'))
if (len(subs),len(vers))!=(54,122):bad(f'raw counts={len(subs)}/{len(vers)}, expected 54/122')
with (R/'archive/manifest.csv').open(encoding='utf-8',newline='') as f: mc=list(csv.DictReader(f))
mj=json.loads(text(R/'archive/manifest.json')); cb={x['file']:x for x in mc}; jb={x['file']:x for x in mj}; actual={str(p.relative_to(R)) for p in subs+vers}
if len(mc)!=176 or len(mj)!=176 or set(cb)!=actual or set(jb)!=actual:bad('manifest count/file-set mismatch')
kinds=defaultdict(int); plas=defaultdict(int)
for rel,x in cb.items():
 p=R/rel; kinds[x['kind']]+=1
 if int(x['size'])!=p.stat().st_size or x['sha256']!=sha(p):bad(f'{rel}: size/SHA mismatch')
 ap=b'PLA88' in p.read_bytes(); dp=x['pla88'].lower()=='true'
 if ap!=dp:bad(f'{rel}: PLA88 flag mismatch')
 if dp:plas[x['kind']]+=1
 y=jb[rel]
 for k in ('kind','code','version','url','file','sha256'):
  if str(y.get(k,''))!=str(x.get(k,'')):bad(f'{rel}: CSV/JSON manifest mismatch {k}')
 if int(y['size'])!=int(x['size']) or bool(y['pla88'])!=dp:bad(f'{rel}: CSV/JSON size/PLA mismatch')
 q=parse_qs(urlparse(x['url']).query)
 if x['kind']=='subject' and (q.get('subject',[''])[0]!=x['code'] or x['version']):bad(f'{rel}: subject identity mismatch')
 if x['kind']=='version' and q.get('version',[''])[0]!=x['version']:bad(f'{rel}: version identity mismatch')
if dict(kinds)!={'subject':54,'version':122} or plas.get('subject',0)!=0 or plas.get('version',0)!=106:bad(f'manifest kind/PLA counts bad: {dict(kinds)} / {dict(plas)}')
ok('raw archive + CSV/JSON manifests: counts, identities, sizes and SHA-256')

# Original source exports
alls=summary(R/'sources/subject_list_vsechny_summary.txt'); valid=summary(R/'sources/subject_list_platne_summary.txt'); codes={p.stem.removeprefix('subject_') for p in subs}
if len(alls)!=54 or set(alls)!=codes:bad('54-subject summary mismatch')
if len(valid)!=14:bad('14-subject current/future summary mismatch')
uc=re.findall(r'[?&]subject=(\d{3,4}-\d{4})',text(R/'sources/Vsechny-predmety.txt'))
if len(uc)!=54 or set(uc)!=codes:bad('Vsechny-predmety.txt mismatch')
canon={'Vsechny-predmety.txt':'30a5238b442d36a9ff787e260571346f2b8634e012d43a2c33df42073eca74cd','official-edison-exports/subject_list_platne.pdf':'c039116a78a8fcd888f9c39f154bc2b2d4b485a3cd23cf1aabef48606719efea','official-edison-exports/subject_list_platne.xls':'d00496f926f53ca6d826d3cc2969b93222b2236ba4a82841c532ace51d45f13f','official-edison-exports/subject_list_vsechny.pdf':'7dc3d38037927e3ebcbc563100ed4c75211f249fed40d7a56a898f51a3e5c4b1','official-edison-exports/subject_list_vsechny.xls':'7b4c0cbcbc915232c353223ee3ddc1a24ffe1620c747958b65a107e8481b8558'}
listed={}
for ln in text(R/'sources/source-files.sha256').splitlines():
 if ln.strip(): d,p=ln.split(None,1); listed[p.strip()]=d
if listed!=canon:bad('source-files.sha256 paths/digests differ from canonical set')
for rel,d in canon.items():
 p=R/'sources'/rel
 if not p.exists() or sha(p)!=d:bad(f'sources/{rel}: missing/SHA mismatch')
ok('official inputs: URL list, 14/54 summaries and five original SHA-256 values')

# data.js + CSV + raw page metadata
m=re.fullmatch(r'\s*window\.PLACHA_DATA\s*=\s*(\[.*\])\s*;?\s*',text(R/'data.js'),re.S); data=json.loads(m.group(1)) if m else []
with (R/'Placha_versions_verified.csv').open(encoding='utf-8',newline='') as f: vc=list(csv.DictReader(f))
if len(data)!=106 or len(vc)!=106 or len({x[0] for x in data})!=106 or len({x['version'] for x in vc})!=106:bad('data.js/verified CSV count or uniqueness mismatch')
db={x[0]:x for x in data}; vb={x['version']:x for x in vc}
if set(db)!=set(vb):bad('data.js/verified CSV version sets differ')
rm={}; names=defaultdict(set)
for v,d in db.items():
 c=vb[v]; code=v.split('/')[0]; names[code].add(d[1]); exp={'code':code,'name':d[1],'introduced':d[2],'cancelled':d[3],'valid_or_future_export':str(d[4]),'focus_2025_2026':str(d[5]),'sha256':d[6]}
 for k,z in exp.items():
  if c[k]!=z:bad(f'{v}: data/CSV mismatch {k}')
 rel=f'archive/versions/version_{v.replace("/","_")}.html'; p=R/rel
 if c['offline_file']!=rel or not p.exists():bad(f'{v}: offline path invalid')
 if parse_qs(urlparse(c['edison_url']).query).get('version',[''])[0]!=v:bad(f'{v}: Edison URL invalid')
 if cb[rel]['sha256']!=d[6] or cb[rel]['pla88'].lower()!='true':bad(f'{v}: manifest backing invalid')
 z=meta(p); rm[v]=z
 if not z['role'] or c['role_PLA88']!=z['role']:bad(f'{v}: role mismatch CSV/raw')
 if page_name(p,v)!=d[1]:bad(f'{v}: data/raw-version name mismatch: {d[1]!r}/{page_name(p,v)!r}')
source_diffs={}
for code,ns in names.items():
 if len(ns)!=1:bad(f'{code}: multiple data names');continue
 n=next(iter(ns)); rn=page_name(R/f'archive/subjects/subject_{code}.html',code)
 if rn!=n:bad(f'{code}: data/raw-subject name mismatch: {n!r}/{rn!r}')
 if alls.get(code)!=n:source_diffs[code]=(alls.get(code),n)
if source_diffs!=KNOWN_NAME_DIFF:bad(f'known Edison source-name differences changed: {source_diffs}')
doc=text(R/'archive/source-discrepancies.md')
for code,(a,b) in KNOWN_NAME_DIFF.items():
 if code not in doc or a not in doc or b not in doc:bad('source discrepancy is not fully documented')
valid_codes={x[0].split('/')[0] for x in data if x[4]}
if valid_codes!=set(valid):bad('current/future data code set != official 14-code export')
foc=[]
for x in data:
 iy=int(x[2].split('/')[0]) if x[2] else 9999; expected=bool(x[4]) and (x[3]=='2025/2026' or (not x[3] and iy<=2025))
 if bool(x[5])!=expected:bad(f'{x[0]}: 2025/26 focus flag mismatch')
 if x[5]:foc.append(x)
if len(foc)!=28 or len({x[0].split('/')[0] for x in foc})!=14:bad('2025/26 slice != 28 versions / 14 subjects')
ok('data layer: 106 versions match raw names, roles, URLs, hashes and focus rule; known source difference documented')

# Conservative UI grouping
by=defaultdict(list)
for x in data:by[x[0].split('/')[0]].append(x)
membership={}; pairs=[]; singles=[]
for code,xs in by.items():
 buckets=defaultdict(list)
 for x in xs:
  z=rm[x[0]]; buckets[(x[2],x[3],z['credits'],'\x1e'.join(z['forms']))].append(x[0])
 gi=0
 for _,items in sorted(buckets.items(),key=lambda q:(q[0][0],sorted(q[1])[0])):
  items=sorted(items); ls=[lang(rm[v]['lang']) for v in items]; groups=[items] if len(items)==2 and set(ls)=={'CZ','EN'} else [[v] for v in items]
  if len(groups)==1 and len(groups[0])==2:pairs.append(tuple(groups[0]))
  else:singles.extend(v for g in groups for v in g)
  for g in groups:
   for v in g:membership[v]=(code,gi)
   gi+=1
if membership.get('9360-0120/02')!=membership.get('9360-0120/04') or membership.get('9360-0120/03')!=membership.get('9360-0120/05'):bad('9360-0120 CZ/EN pairs not grouped')
if membership.get('9360-0131/02')==membership.get('9360-0131/04'):bad('9360-0131 two CZ versions incorrectly grouped')
idx=text(R/'index.html')
for marker in ('function formSignature','function buildGenerations','m.forms.map',"items.length===2","langs.includes('CZ')","langs.includes('EN')"):
 if marker not in idx:bad(f'index missing grouping marker {marker}')
ok(f'UI grouping: {len(pairs)} unambiguous CZ/EN pairs, {len(singles)} standalone variants; {sum(len(z["forms"])>1 for z in rm.values())} multi-form versions preserved')

# Web syntax, local links, archive index and hygiene
for i,js in enumerate(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',idx,re.S),1):
 with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:f.write(js); tmp=f.name
 p=subprocess.run(['node','--check',tmp],capture_output=True,text=True); Path(tmp).unlink(missing_ok=True)
 if p.returncode:bad(f'index inline JS #{i} syntax error: {p.stderr.strip()}')
for page in (R/'index.html',R/'archive/index.html'):
 t=text(page)
 if 'drive.google.com' in t:bad(f'Drive URL remains in {page.relative_to(R)}')
 for href in re.findall(r'href="([^"]+)"',t):
  if href.startswith(('http://','https://','#')) or '${' in href:continue
  if href and not (page.parent/href.split('#')[0].split('?')[0]).resolve().exists():bad(f'{page.relative_to(R)} broken href {href}')
for p in [R/'README.md',R/'data.js',R/'Placha_versions_verified.csv',*list((R/'sources').glob('*.txt')),*list((R/'sources').glob('*.sha256')),*list((R/'sources/official-edison-exports').glob('*.md'))]:
 if 'drive.google.com' in text(p):bad(f'Drive URL remains in {p.relative_to(R)}')
ai=text(R/'archive/index.html')
for p in subs+vers:
 if str(p.relative_to(R/'archive')) not in ai:bad(f'archive index misses {p.relative_to(R/"archive")}')
readme=text(R/'README.md')
for tok in ('54 hlavních','122 stránek','106 verzí','28 verzí / 14 předmětů'):
 if tok not in readme:bad(f'README misses {tok}')
complete=dict(x.split('=',1) for x in text(R/'archive/.complete').splitlines() if '=' in x); report=dict(x.split('=',1) for x in text(R/'archive/report-build.txt').splitlines() if '=' in x)
if complete!={'subjects':'54','versions':'122','pla88_versions':'106'}:bad(f'.complete mismatch {complete}')
for k,v in {'versions_with_PLA88':'106','subjects_with_PLA88':'54','focus_2025_2026_versions':'28','focus_2025_2026_subjects':'14','new_vs_original':'9360-0125/02'}.items():
 if report.get(k)!=v:bad(f'report-build {k} mismatch')
if (R/'.pages-enabled').exists():bad('.pages-enabled stale trigger remains')
if sorted(p.name for p in (R/'.github/workflows').glob('*.yml'))!=['consistency.yml','pages.yml']:bad('workflow set is not exactly consistency.yml + pages.yml')
ok('web/project hygiene: JS parses, local links resolve, archive index covers raw pages, no Drive URL or temporary workflow remains')

print('=== PROJECT CONSISTENCY AUDIT ===')
for x in OK:print('OK  ',x)
for x in E:print('FAIL',x)
print(f'\nSUMMARY: {len(E)} failures, {len(OK)} check groups')
sys.exit(1 if E else 0)

#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html as htmlmod
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
notes: list[str] = []

def fail(msg: str) -> None: errors.append(msg)
def note(msg: str) -> None: notes.append(msg)

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def strip_tags(s: str) -> str:
    return re.sub(r'\s+',' ',htmlmod.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def meta_value(text: str,label: str)->str:
    m=re.search(rf'<td class="label"><span class="outputText">{re.escape(label)}</span></td><td class="value">(?:<span class="outputText">)?(.*?)(?:</span>)?</td>',text,re.S)
    return strip_tags(m.group(1)) if m else ''

def table_block(text: str,table_id: str)->str:
    m=re.search(rf'<table id="{re.escape(table_id)}".*?</table>',text,re.S)
    return m.group(0) if m else ''

def table_rows(block: str)->list[list[str]]:
    body=re.search(r'<tbody[^>]*>(.*?)</tbody>',block,re.S)
    if not body:return []
    return [[strip_tags(td) for td in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)] for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',body.group(1),re.S)]

def role_pla88(text: str)->str:
    body=re.search(r'<tbody[^>]*>(.*?)</tbody>',table_block(text,'form1:tableTeachers'),re.S)
    if not body:return ''
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',body.group(1),re.S):
        tds=re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)
        if len(tds)>=4 and strip_tags(tds[0])=='PLA88':
            c='selected-green.png' in tds[2]; p='selected-green.png' in tds[3]
            if c and p:return 'cvičící + přednášející'
            if c:return 'cvičící'
            if p:return 'přednášející'
            return 'uvedena bez označené role'
    return ''

def version_meta(path: Path)->dict:
    text=path.read_text(encoding='utf-8',errors='replace')
    forms=table_rows(table_block(text,'form1:tableForms'))
    return {'language':meta_value(text,'Jazyk výuky'),'credits':meta_value(text,'Kredity'),'faculty':meta_value(text,'Určeno pro fakulty'),'study':meta_value(text,'Určeno pro typy studia'),'forms':[' | '.join(r[:3]) for r in forms if r],'role':role_pla88(text)}

def parse_summary(path: Path)->dict[str,str]:
    out={}
    for code,name in re.findall(r'(?m)^(\d{3,4}-\d{4})\t(.+)$',path.read_text(encoding='utf-8')):out[code]=name.strip()
    return out

def norm_lang(s:str)->str:
    s=s.lower()
    if 'češt' in s:return 'CZ'
    if 'anglič' in s:return 'EN'
    return s

def full_form_sig(meta:dict)->str:
    return '\x1e'.join(meta['forms'])

# 1) Raw archive and manifests
subjects=sorted((ROOT/'archive/subjects').glob('subject_*.html')); versions=sorted((ROOT/'archive/versions').glob('version_*.html'))
if len(subjects)!=54:fail(f'subject HTML count={len(subjects)}, expected 54')
if len(versions)!=122:fail(f'version HTML count={len(versions)}, expected 122')
with (ROOT/'archive/manifest.csv').open(encoding='utf-8',newline='') as f: mc=list(csv.DictReader(f))
mj=json.loads((ROOT/'archive/manifest.json').read_text(encoding='utf-8'))
if len(mc)!=176 or len(mj)!=176:fail(f'manifest row counts CSV/JSON={len(mc)}/{len(mj)}, expected 176/176')
mc_by={r['file']:r for r in mc}; mj_by={r['file']:r for r in mj}; actual={str(p.relative_to(ROOT)) for p in subjects+versions}
if set(mc_by)!=actual:fail(f'manifest CSV file set mismatch: missing={sorted(set(mc_by)-actual)}, extra={sorted(actual-set(mc_by))}')
if set(mj_by)!=actual:fail('manifest JSON file set differs from raw archive')
kind_count=defaultdict(int); pla_count=defaultdict(int)
for rel,row in mc_by.items():
    p=ROOT/rel; kind_count[row['kind']]+=1
    if not p.exists():continue
    if int(row['size'])!=p.stat().st_size:fail(f'{rel}: size mismatch')
    if row['sha256']!=sha256(p):fail(f'{rel}: SHA-256 mismatch')
    actual_pla=b'PLA88' in p.read_bytes(); declared=row['pla88'].lower()=='true'
    if actual_pla!=declared:fail(f'{rel}: PLA88 manifest={declared}, actual={actual_pla}')
    if declared:pla_count[row['kind']]+=1
    jr=mj_by[rel]
    for k in ('kind','code','version','url','file','sha256'):
        if str(jr.get(k,''))!=str(row.get(k,'')):fail(f'{rel}: CSV/JSON manifest mismatch in {k}')
    if int(jr['size'])!=int(row['size']) or bool(jr['pla88'])!=declared:fail(f'{rel}: CSV/JSON manifest mismatch in size/pla88')
    q=parse_qs(urlparse(row['url']).query)
    if row['kind']=='subject':
        if q.get('subject',[''])[0]!=row['code'] or row['version']:fail(f'{rel}: malformed subject manifest identity')
    elif row['kind']=='version':
        if q.get('version',[''])[0]!=row['version']:fail(f'{rel}: malformed version manifest identity')
        txt=p.read_text(encoding='utf-8',errors='replace')
        if row['version'] not in txt:fail(f'{rel}: version identifier absent from archived HTML')
if dict(kind_count)!={'subject':54,'version':122}:fail(f'manifest kind counts={dict(kind_count)}')
if pla_count.get('subject',0)!=0 or pla_count.get('version',0)!=106:fail(f'manifest PLA88 counts={dict(pla_count)}, expected subject=0/version=106')
note('raw archive: 54 + 122 files; both manifests match actual files, identities, sizes and SHA-256')

# 2) Sources and official exports
all_summary=parse_summary(ROOT/'sources/subject_list_vsechny_summary.txt'); valid_summary=parse_summary(ROOT/'sources/subject_list_platne_summary.txt')
subject_codes={p.stem.removeprefix('subject_') for p in subjects}
if len(all_summary)!=54 or set(all_summary)!=subject_codes:fail('official all-subject summary != 54 archived subject codes')
if len(valid_summary)!=14:fail(f'official current/future summary count={len(valid_summary)}, expected 14')
url_text=(ROOT/'sources/Vsechny-predmety.txt').read_text(encoding='utf-8')
url_codes=re.findall(r'[?&]subject=(\d{3,4}-\d{4})',url_text)
if len(url_codes)!=54 or set(url_codes)!=subject_codes:fail(f'Vsechny-predmety.txt code set/count mismatch: {len(url_codes)}')
known={'Vsechny-predmety.txt':'30a5238b442d36a9ff787e260571346f2b8634e012d43a2c33df42073eca74cd','official-edison-exports/subject_list_platne.pdf':'c039116a78a8fcd888f9c39f154bc2b2d4b485a3cd23cf1aabef48606719efea','official-edison-exports/subject_list_platne.xls':'d00496f926f53ca6d826d3cc2969b93222b2236ba4a82841c532ace51d45f13f','official-edison-exports/subject_list_vsechny.pdf':'7dc3d38037927e3ebcbc563100ed4c75211f249fed40d7a56a898f51a3e5c4b1','official-edison-exports/subject_list_vsechny.xls':'7b4c0cbcbc915232c353223ee3ddc1a24ffe1620c747958b65a107e8481b8558'}
listed={}
for line in (ROOT/'sources/source-files.sha256').read_text(encoding='utf-8').splitlines():
    if line.strip():d,p=line.split(None,1);listed[p.strip()]=d
if listed!=known:fail(f'source-files.sha256 entries differ from canonical set: {listed}')
for rel,digest in known.items():
    p=ROOT/'sources'/rel
    if not p.exists():fail(f'missing source input: sources/{rel}')
    elif sha256(p)!=digest:fail(f'sources/{rel}: SHA-256 mismatch')
note('source inputs: 54 URL list + 14/54 official summaries + all five canonical SHA-256 values verified')

# 3) data.js and verified CSV
m=re.fullmatch(r'\s*window\.PLACHA_DATA\s*=\s*(\[.*\])\s*;?\s*',(ROOT/'data.js').read_text(encoding='utf-8'),re.S)
if not m:fail('data.js unexpected format');data=[]
else:data=json.loads(m.group(1))
with (ROOT/'Placha_versions_verified.csv').open(encoding='utf-8',newline='') as f: vr=list(csv.DictReader(f))
if len(data)!=106 or len(vr)!=106:fail(f'data/CSV row counts={len(data)}/{len(vr)}, expected 106/106')
if len({r[0] for r in data})!=106 or len({r['version'] for r in vr})!=106:fail('duplicate version IDs in data layer')
db={r[0]:r for r in data}; cb={r['version']:r for r in vr}
if set(db)!=set(cb):fail('data.js and verified CSV version sets differ')
raw_meta={}; names_by_code=defaultdict(set)
for v,d in db.items():
    c=cb[v];names_by_code[v.split('/')[0]].add(d[1])
    exp={'code':v.split('/')[0],'name':d[1],'introduced':d[2],'cancelled':d[3],'valid_or_future_export':str(d[4]),'focus_2025_2026':str(d[5]),'sha256':d[6]}
    for k,val in exp.items():
        if c[k]!=val:fail(f'{v}: data.js/CSV mismatch in {k}: {c[k]!r}!={val!r}')
    rel=f'archive/versions/version_{v.replace("/","_")}.html'
    if c['offline_file']!=rel or not (ROOT/rel).exists():fail(f'{v}: invalid offline_file')
    if parse_qs(urlparse(c['edison_url']).query).get('version',[''])[0]!=v:fail(f'{v}: invalid Edison URL')
    if mc_by[rel]['sha256']!=d[6] or mc_by[rel]['pla88'].lower()!='true':fail(f'{v}: data not backed by PLA88 manifest row')
    meta=version_meta(ROOT/rel);raw_meta[v]=meta
    if not meta['role']:fail(f'{v}: PLA88 role cannot be parsed from raw HTML')
    if c['role_PLA88']!=meta['role']:fail(f'{v}: CSV role={c["role_PLA88"]!r}, raw role={meta["role"]!r}')
for code,names in names_by_code.items():
    if len(names)!=1:fail(f'{code}: multiple names in data.js: {sorted(names)}')
    name=next(iter(names))
    if all_summary.get(code)!=name:fail(f'{code}: data name={name!r}, official summary name={all_summary.get(code)!r}')
valid_codes={r[0].split('/')[0] for r in data if r[4]}
if valid_codes!=set(valid_summary):fail(f'valid/current code set differs from official export: data-only={sorted(valid_codes-set(valid_summary))}, source-only={sorted(set(valid_summary)-valid_codes)}')
focus=[]
for r in data:
    v,_,intro,cancel,valid,flag,_=r;iy=int(intro.split('/')[0]) if intro else 9999
    expected=bool(valid) and (cancel=='2025/2026' or (not cancel and iy<=2025))
    if bool(flag)!=expected:fail(f'{v}: focus flag={flag}, rule={int(expected)}')
    if flag:focus.append(r)
if len(focus)!=28 or len({r[0].split('/')[0] for r in focus})!=14:fail('focus slice != 28 versions / 14 subjects')
note('data layer: 106 unique versions; names, roles, URLs, hashes and 2025/26 flags all match primary/archive evidence')

# 4) Conservative generation model used by the UI
by_code=defaultdict(list)
for r in data:by_code[r[0].split('/')[0]].append(r)
pairs=[];singles=[];generation_membership={}
multiform=sum(1 for m in raw_meta.values() if len(m['forms'])>1)
for code,rows in by_code.items():
    buckets=defaultdict(list)
    for r in rows:
        m=raw_meta[r[0]];key=(r[2],r[3],str(m['credits']),full_form_sig(m));buckets[key].append(r[0])
    gi=0
    for key,items in sorted(buckets.items(),key=lambda kv:(kv[0][0],sorted(kv[1])[0])):
        items=sorted(items);langs=[norm_lang(raw_meta[v]['language']) for v in items]
        if len(items)==2 and set(langs)=={'CZ','EN'}:
            group=items;pairs.append(tuple(items))
        else:
            for v in items:
                group=[v];singles.append(v);generation_membership[v]=(code,gi);gi+=1
            continue
        for v in group:generation_membership[v]=(code,gi)
        gi+=1
if generation_membership.get('9360-0120/02')!=generation_membership.get('9360-0120/04'):fail('9360-0120/02 + /04 should form one CZ/EN generation')
if generation_membership.get('9360-0120/03')!=generation_membership.get('9360-0120/05'):fail('9360-0120/03 + /05 should form one CZ/EN generation')
if generation_membership.get('9360-0131/02')==generation_membership.get('9360-0131/04'):fail('9360-0131/02 + /04 are both CZ and must remain separate')
index=(ROOT/'index.html').read_text(encoding='utf-8')
for marker in ('function formSignature','function buildGenerations','m.forms.map','items.length===2','langs.includes(\'CZ\')','langs.includes(\'EN\')'):
    if marker not in index:fail(f'index.html missing conservative grouping marker: {marker}')
note(f'UI grouping model: {len(pairs)} unambiguous CZ/EN pairs, {len(singles)} standalone variants; {multiform} versions preserve multiple study forms')

# 5) Main web syntax, local links and stale dependencies
inline_scripts=re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',index,re.S)
for i,js in enumerate(inline_scripts,1):
    with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:f.write(js);tmp=f.name
    p=subprocess.run(['node','--check',tmp],capture_output=True,text=True)
    Path(tmp).unlink(missing_ok=True)
    if p.returncode:fail(f'index.html inline JavaScript #{i} syntax error: {p.stderr.strip()}')
for page in (ROOT/'index.html',ROOT/'archive/index.html'):
    txt=page.read_text(encoding='utf-8',errors='replace')
    if 'drive.google.com' in txt:fail(f'stale Google Drive URL in {page.relative_to(ROOT)}')
    for href in re.findall(r'href="([^"]+)"',txt):
        if href.startswith(('http://','https://','#')) or '${' in href:continue
        target=(page.parent/href.split('#')[0].split('?')[0]).resolve()
        if href and not target.exists():fail(f'{page.relative_to(ROOT)} broken local href: {href}')
for p in [ROOT/'README.md',ROOT/'data.js',ROOT/'Placha_versions_verified.csv']+list((ROOT/'sources').glob('*.txt'))+list((ROOT/'sources').glob('*.sha256'))+list((ROOT/'sources/official-edison-exports').glob('*.md')):
    if 'drive.google.com' in p.read_text(encoding='utf-8',errors='replace'):fail(f'stale Google Drive URL in {p.relative_to(ROOT)}')
# Archive index should link every raw page at least once.
archive_index=(ROOT/'archive/index.html').read_text(encoding='utf-8',errors='replace')
for p in subjects+versions:
    rel=str(p.relative_to(ROOT/'archive'))
    if rel not in archive_index:fail(f'archive/index.html does not reference {rel}')
# README/count marker consistency.
readme=(ROOT/'README.md').read_text(encoding='utf-8')
for token in ('54 hlavních','122 stránek','106 verzí','28 verzí / 14 předmětů'):
    if token not in readme:fail(f'README missing expected summary token: {token}')
complete=dict(line.split('=',1) for line in (ROOT/'archive/.complete').read_text().splitlines() if '=' in line)
report=dict(line.split('=',1) for line in (ROOT/'archive/report-build.txt').read_text().splitlines() if '=' in line)
if complete!={'subjects':'54','versions':'122','pla88_versions':'106'}:fail(f'archive/.complete inconsistent: {complete}')
for k,v in {'versions_with_PLA88':'106','subjects_with_PLA88':'54','focus_2025_2026_versions':'28','focus_2025_2026_subjects':'14','new_vs_original':'9360-0125/02'}.items():
    if report.get(k)!=v:fail(f'archive/report-build.txt {k}={report.get(k)!r}, expected {v!r}')
if (ROOT/'.pages-enabled').exists():fail('.pages-enabled stale trigger still exists')
note('web/project hygiene: JavaScript parses, local links resolve, archive index covers all raw pages, no Drive URLs remain')

print('=== PROJECT CONSISTENCY AUDIT ===')
for x in notes:print('OK   ',x)
for x in errors:print('FAIL ',x)
print(f'\nSUMMARY: {len(errors)} failures, {len(notes)} check groups')
if errors:sys.exit(1)

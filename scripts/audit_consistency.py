#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html as htmlmod
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
warnings: list[str] = []
notes: list[str] = []

def fail(msg: str) -> None: errors.append(msg)
def warn(msg: str) -> None: warnings.append(msg)
def note(msg: str) -> None: notes.append(msg)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def strip_tags(s: str) -> str:
    return re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

def meta_value(text: str, label: str) -> str:
    pat = re.compile(rf'<td class="label"><span class="outputText">{re.escape(label)}</span></td><td class="value">(?:<span class="outputText">)?(.*?)(?:</span>)?</td>', re.S)
    m = pat.search(text)
    return strip_tags(m.group(1)) if m else ''

def table_block(text: str, table_id: str) -> str:
    m = re.search(rf'<table id="{re.escape(table_id)}".*?</table>', text, re.S)
    return m.group(0) if m else ''

def table_rows(block: str) -> list[list[str]]:
    body = re.search(r'<tbody[^>]*>(.*?)</tbody>', block, re.S)
    if not body:
        return []
    out = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', body.group(1), re.S):
        out.append([strip_tags(td) for td in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)])
    return out

def role_pla88(text: str) -> str:
    block = table_block(text, 'form1:tableTeachers')
    body = re.search(r'<tbody[^>]*>(.*?)</tbody>', block, re.S)
    if not body:
        return ''
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', body.group(1), re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if len(tds) >= 4 and strip_tags(tds[0]) == 'PLA88':
            c = 'selected-green.png' in tds[2]
            p = 'selected-green.png' in tds[3]
            if c and p: return 'cvičící + přednášející'
            if c: return 'cvičící'
            if p: return 'přednášející'
            return 'uvedena bez označené role'
    return ''

def version_meta(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='replace')
    forms = table_rows(table_block(text, 'form1:tableForms'))
    return {
        'language': meta_value(text, 'Jazyk výuky'),
        'credits': meta_value(text, 'Kredity'),
        'faculty': meta_value(text, 'Určeno pro fakulty'),
        'study': meta_value(text, 'Určeno pro typy studia'),
        'forms': [' | '.join(r[:3]) for r in forms if r],
        'role': role_pla88(text),
    }

def parse_summary_codes(path: Path) -> list[str]:
    return re.findall(r'(?m)^(\d{3,4}-\d{4})\t', path.read_text(encoding='utf-8'))

# Raw archive + manifests
subjects = sorted((ROOT/'archive/subjects').glob('subject_*.html'))
versions = sorted((ROOT/'archive/versions').glob('version_*.html'))
if len(subjects) != 54: fail(f'archive/subjects count={len(subjects)}, expected 54')
if len(versions) != 122: fail(f'archive/versions count={len(versions)}, expected 122')
note(f'raw archive: {len(subjects)} subject pages + {len(versions)} version pages')

with (ROOT/'archive/manifest.csv').open(encoding='utf-8', newline='') as f:
    manifest_csv = list(csv.DictReader(f))
manifest_json = json.loads((ROOT/'archive/manifest.json').read_text(encoding='utf-8'))
if len(manifest_csv) != 176: fail(f'manifest.csv rows={len(manifest_csv)}, expected 176')
if len(manifest_json) != 176: fail(f'manifest.json rows={len(manifest_json)}, expected 176')
json_by_file = {r['file']: r for r in manifest_json}
csv_by_file = {r['file']: r for r in manifest_csv}
if set(json_by_file) != set(csv_by_file): fail('manifest CSV and JSON contain different file sets')
actual_paths = {str(p.relative_to(ROOT)) for p in subjects + versions}
if set(csv_by_file) != actual_paths:
    fail(f'manifest/file-set mismatch; missing={sorted(set(csv_by_file)-actual_paths)}, extra={sorted(actual_paths-set(csv_by_file))}')
pla88_manifest = 0
for rel, row in csv_by_file.items():
    p = ROOT/rel
    if not p.exists():
        continue
    if int(row['size']) != p.stat().st_size: fail(f'{rel}: size mismatch')
    actual_sha = sha256(p)
    if row['sha256'] != actual_sha: fail(f'{rel}: SHA-256 mismatch')
    actual_pla88 = b'PLA88' in p.read_bytes()
    declared = row['pla88'].lower() == 'true'
    if actual_pla88 != declared: fail(f'{rel}: pla88 manifest={declared}, actual={actual_pla88}')
    if declared: pla88_manifest += 1
    jr = json_by_file[rel]
    for key in ('kind','code','version','url','file','sha256'):
        if str(jr.get(key,'')) != str(row.get(key,'')): fail(f'{rel}: manifest CSV/JSON differ in {key}')
    if int(jr['size']) != int(row['size']) or bool(jr['pla88']) != declared: fail(f'{rel}: manifest CSV/JSON differ in size/pla88')
if pla88_manifest != 106: fail(f'manifest PLA88 count={pla88_manifest}, expected 106')
note(f'manifests: 176/176 files, SHA-256 and size verified; PLA88={pla88_manifest}')

# data.js + verified CSV
text = (ROOT/'data.js').read_text(encoding='utf-8')
m = re.fullmatch(r'\s*window\.PLACHA_DATA\s*=\s*(\[.*\])\s*;?\s*', text, re.S)
if not m:
    fail('data.js unexpected format'); data=[]
else:
    data = json.loads(m.group(1))
if len(data) != 106: fail(f'data.js rows={len(data)}, expected 106')
if len({r[0] for r in data}) != len(data): fail('data.js duplicate version IDs')
with (ROOT/'Placha_versions_verified.csv').open(encoding='utf-8', newline='') as f:
    verified = list(csv.DictReader(f))
if len(verified) != 106: fail(f'verified CSV rows={len(verified)}, expected 106')
if len({r['version'] for r in verified}) != len(verified): fail('verified CSV duplicate version IDs')
verified_by_v = {r['version']:r for r in verified}
data_by_v = {r[0]:r for r in data}
if set(verified_by_v) != set(data_by_v): fail('data.js and verified CSV contain different version sets')
for v,d in data_by_v.items():
    c = verified_by_v[v]
    expected = {'name':d[1],'introduced':d[2],'cancelled':d[3],'valid_or_future_export':str(d[4]),'focus_2025_2026':str(d[5]),'sha256':d[6]}
    for k,val in expected.items():
        if c[k] != val: fail(f'{v}: data.js/CSV mismatch in {k}')
    rel = c['offline_file']
    if rel != f'archive/versions/version_{v.replace("/","_")}.html' or not (ROOT/rel).exists(): fail(f'{v}: bad offline_file {rel}')
    if parse_qs(urlparse(c['edison_url']).query).get('version',[''])[0] != v: fail(f'{v}: bad Edison URL')
    mr = csv_by_file.get(rel)
    if not mr or mr['sha256'] != d[6] or mr['pla88'].lower() != 'true': fail(f'{v}: no matching PLA88=true manifest row')

# Official exported code sets + focus rule
valid_summary = set(parse_summary_codes(ROOT/'sources/subject_list_platne_summary.txt'))
all_summary = set(parse_summary_codes(ROOT/'sources/subject_list_vsechny_summary.txt'))
subject_codes = {p.stem.removeprefix('subject_') for p in subjects}
if len(valid_summary) != 14: fail(f'valid summary codes={len(valid_summary)}, expected 14')
if len(all_summary) != 54: fail(f'all summary codes={len(all_summary)}, expected 54')
if all_summary != subject_codes: fail('54-code source summary != archived subject pages')
data_valid_codes = {r[0].split('/')[0] for r in data if r[4]}
if data_valid_codes != valid_summary:
    fail(f'current/future code set differs: data-only={sorted(data_valid_codes-valid_summary)}, summary-only={sorted(valid_summary-data_valid_codes)}')
focus=[]
for r in data:
    v,_,introduced,cancelled,valid,focus_flag,_ = r
    intro_year = int(introduced.split('/')[0]) if introduced else 9999
    expected_focus = bool(valid) and (cancelled=='2025/2026' or (not cancelled and intro_year<=2025))
    if bool(focus_flag) != expected_focus: fail(f'{v}: focus={focus_flag}, rule={int(expected_focus)}')
    if focus_flag: focus.append(r)
if len(focus) != 28 or len({r[0].split('/')[0] for r in focus}) != 14: fail('focus set != 28 versions / 14 subjects')
note('data layer: 106 unique versions; official current/future=14 codes; focus=28 versions / 14 subjects')

# Role column + UI grouping heuristic
raw_meta={}; blank_roles=[]; wrong_roles=[]
for v,row in verified_by_v.items():
    meta = version_meta(ROOT/row['offline_file']); raw_meta[v]=meta
    actual = str(meta['role']); stored = row.get('role_PLA88','').strip()
    if not stored: blank_roles.append(v)
    elif stored != actual: wrong_roles.append((v,stored,actual))
if wrong_roles: fail(f'role_PLA88 disagrees with raw HTML: {wrong_roles}')
if blank_roles: warn(f'role_PLA88 blank for {len(blank_roles)}/106 CSV rows although raw HTML yields roles')

def first_extent(meta:dict)->str:
    forms=meta['forms']; return '—' if not forms else str(forms[0]).split(' | ')[-1]
by_code=defaultdict(list)
for r in data: by_code[r[0].split('/')[0]].append(r)
ambiguous=[]; multi_form=[]
for code,rows in by_code.items():
    gens=defaultdict(list)
    for r in rows:
        meta=raw_meta[r[0]]
        if len(meta['forms'])>1: multi_form.append((r[0],meta['forms']))
        key=(r[2],r[3],str(meta['credits']),first_extent(meta))
        gens[key].append((r[0],str(meta['language']),str(meta['faculty']),str(meta['study'])))
    for key,items in gens.items():
        norm=[('CZ' if 'češt' in x[1].lower() else 'EN' if 'anglič' in x[1].lower() else x[1]) for x in items]
        dup=[k for k,n in Counter(norm).items() if n>1]
        if len(items)>2 or dup: ambiguous.append((code,key,items,dup))
if ambiguous: warn('UI generation heuristic has ambiguous groups: '+repr(ambiguous))
if multi_form: warn(f'{len(multi_form)} versions have multiple study-form rows; UI groups using first row only: {multi_form}')
else: note('UI generation: no version has multiple study-form rows')
if not ambiguous: note('UI generation: no generation combines duplicate-language variants')

# Source inputs + hash list usability
hash_lines=[]
for line in (ROOT/'sources/source-files.sha256').read_text(encoding='utf-8').splitlines():
    if line.strip():
        digest,rel=line.split(None,1); hash_lines.append((digest,rel.strip()))
missing_hash_paths=[]; bad_hash=[]
for digest,rel in hash_lines:
    p=ROOT/'sources'/rel
    if not p.exists(): missing_hash_paths.append(rel)
    elif sha256(p)!=digest: bad_hash.append(rel)
if missing_hash_paths: warn(f'source-files.sha256 not directly checkable from sources/: missing {missing_hash_paths}')
if bad_hash: fail(f'source input SHA mismatches: {bad_hash}')
known={'Vsechny-predmety.txt':'30a5238b442d36a9ff787e260571346f2b8634e012d43a2c33df42073eca74cd','official-edison-exports/subject_list_platne.pdf':'c039116a78a8fcd888f9c39f154bc2b2d4b485a3cd23cf1aabef48606719efea','official-edison-exports/subject_list_platne.xls':'d00496f926f53ca6d826d3cc2969b93222b2236ba4a82841c532ace51d45f13f','official-edison-exports/subject_list_vsechny.pdf':'7dc3d38037927e3ebcbc563100ed4c75211f249fed40d7a56a898f51a3e5c4b1','official-edison-exports/subject_list_vsechny.xls':'7b4c0cbcbc915232c353223ee3ddc1a24ffe1620c747958b65a107e8481b8558'}
for rel,digest in known.items():
    p=ROOT/'sources'/rel
    if not p.exists(): fail(f'missing source input sources/{rel}')
    elif sha256(p)!=digest: fail(f'sources/{rel}: original SHA mismatch')
note('official source inputs: all 5 known SHA-256 values verified')

# Hygiene, links, markers
if (ROOT/'.pages-enabled').exists(): warn('.pages-enabled is a stale one-time deployment trigger')
for p in [ROOT/'README.md',ROOT/'index.html',ROOT/'data.js',ROOT/'Placha_versions_verified.csv']+list((ROOT/'sources').glob('*.txt'))+list((ROOT/'sources').glob('*.sha256'))+list((ROOT/'sources/official-edison-exports').glob('*.md')):
    if 'drive.google.com' in p.read_text(encoding='utf-8',errors='replace'): fail(f'stale Google Drive URL in {p.relative_to(ROOT)}')
index=(ROOT/'index.html').read_text(encoding='utf-8')
for href in re.findall(r'href="([^"]+)"',index):
    if href.startswith(('http://','https://','#')) or '${' in href: continue
    target=ROOT/href.split('#')[0].split('?')[0]
    if href and not target.exists(): fail(f'index.html static relative link missing: {href}')
complete=dict(line.split('=',1) for line in (ROOT/'archive/.complete').read_text().splitlines() if '=' in line)
report=dict(line.split('=',1) for line in (ROOT/'archive/report-build.txt').read_text().splitlines() if '=' in line)
if complete != {'subjects':'54','versions':'122','pla88_versions':'106'}: fail(f'archive/.complete inconsistent: {complete}')
for k,v in {'versions_with_PLA88':'106','subjects_with_PLA88':'54','focus_2025_2026_versions':'28','focus_2025_2026_subjects':'14','new_vs_original':'9360-0125/02'}.items():
    if report.get(k)!=v: fail(f'archive/report-build.txt {k}={report.get(k)!r}, expected {v!r}')

print('=== PROJECT CONSISTENCY AUDIT ===')
for x in notes: print('OK   ',x)
for x in warnings: print('WARN ',x)
for x in errors: print('FAIL ',x)
print(f'\nSUMMARY: {len(errors)} failures, {len(warnings)} warnings, {len(notes)} checks/notes')
if errors: sys.exit(1)

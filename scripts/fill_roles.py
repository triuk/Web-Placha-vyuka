#!/usr/bin/env python3
import csv, html as htmlmod, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'Placha_versions_verified.csv'

def strip_tags(s):
    return re.sub(r'\s+',' ',htmlmod.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def role(text):
    m=re.search(r'<table id="form1:tableTeachers".*?</table>',text,re.S)
    if not m: return ''
    body=re.search(r'<tbody[^>]*>(.*?)</tbody>',m.group(0),re.S)
    if not body: return ''
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',body.group(1),re.S):
        tds=re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)
        if len(tds)>=4 and strip_tags(tds[0])=='PLA88':
            c='selected-green.png' in tds[2]; p='selected-green.png' in tds[3]
            if c and p: return 'cvičící + přednášející'
            if c: return 'cvičící'
            if p: return 'přednášející'
            return 'uvedena bez označené role'
    return ''

with CSV.open(encoding='utf-8',newline='') as f:
    rows=list(csv.DictReader(f)); fields=list(rows[0].keys())
for r in rows:
    html=(ROOT/r['offline_file']).read_text(encoding='utf-8',errors='replace')
    r['role_PLA88']=role(html)
    if not r['role_PLA88']:
        raise SystemExit(f"Role not found for {r['version']}")
with CSV.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
print(f'Updated role_PLA88 for {len(rows)} rows')

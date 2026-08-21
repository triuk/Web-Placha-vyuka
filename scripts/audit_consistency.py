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

KNOWN_NAME_DIFFERENCES = {
    # Official Edison export has a final period; raw Subject/SubjectVersion pages do not.
    "9360-0903": ("Metody instrumentální analýzy II.", "Metody instrumentální analýzy II"),
}


def fail(msg: str) -> None:
    errors.append(msg)


def note(msg: str) -> None:
    notes.append(msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def meta_value(text: str, label: str) -> str:
    pat = re.compile(
        rf'<td class="label"><span class="outputText">{re.escape(label)}</span></td>'
        rf'<td class="value">(?:<span class="outputText">)?(.*?)(?:</span>)?</td>',
        re.S,
    )
    m = pat.search(text)
    return strip_tags(m.group(1)) if m else ""


def table_block(text: str, table_id: str) -> str:
    m = re.search(rf'<table id="{re.escape(table_id)}".*?</table>', text, re.S)
    return m.group(0) if m else ""


def table_rows(block: str) -> list[list[str]]:
    body = re.search(r"<tbody[^>]*>(.*?)</tbody>", block, re.S)
    if not body:
        return []
    return [
        [strip_tags(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S)
    ]


def role_pla88(text: str) -> str:
    body = re.search(r"<tbody[^>]*>(.*?)</tbody>", table_block(text, "form1:tableTeachers"), re.S)
    if not body:
        return ""
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) >= 4 and strip_tags(tds[0]) == "PLA88":
            exercise = "selected-green.png" in tds[2]
            lecture = "selected-green.png" in tds[3]
            if exercise and lecture:
                return "cvičící + přednášející"
            if exercise:
                return "cvičící"
            if lecture:
                return "přednášející"
            return "uvedena bez označené role"
    return ""


def version_meta(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    forms = table_rows(table_block(text, "form1:tableForms"))
    return {
        "language": meta_value(text, "Jazyk výuky"),
        "credits": meta_value(text, "Kredity"),
        "faculty": meta_value(text, "Určeno pro fakulty"),
        "study": meta_value(text, "Určeno pro typy studia"),
        "forms": [" | ".join(r[:3]) for r in forms if r],
        "role": role_pla88(text),
    }


def page_name(path: Path, identifier: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        rf'<span class="outputText">{re.escape(identifier)}\s+–\s+(.*?)</span>',
        text,
        re.S,
    )
    if not m:
        return ""
    name = strip_tags(m.group(1))
    # Edison appends the short course abbreviation in final parentheses.
    return re.sub(r"\s+\([^()]+\)$", "", name).strip()


def parse_summary(path: Path) -> dict[str, str]:
    return {
        code: name.strip()
        for code, name in re.findall(
            r"(?m)^(\d{3,4}-\d{4})\t(.+)$", path.read_text(encoding="utf-8")
        )
    }


def norm_lang(s: str) -> str:
    s = s.lower()
    if "češt" in s:
        return "CZ"
    if "anglič" in s:
        return "EN"
    return s


def full_form_sig(meta: dict) -> str:
    return "\x1e".join(meta["forms"])


# 1) Raw archive and manifests
subjects = sorted((ROOT / "archive/subjects").glob("subject_*.html"))
versions = sorted((ROOT / "archive/versions").glob("version_*.html"))
if len(subjects) != 54:
    fail(f"subject HTML count={len(subjects)}, expected 54")
if len(versions) != 122:
    fail(f"version HTML count={len(versions)}, expected 122")

with (ROOT / "archive/manifest.csv").open(encoding="utf-8", newline="") as f:
    manifest_csv = list(csv.DictReader(f))
manifest_json = json.loads((ROOT / "archive/manifest.json").read_text(encoding="utf-8"))
if len(manifest_csv) != 176 or len(manifest_json) != 176:
    fail(
        f"manifest row counts CSV/JSON={len(manifest_csv)}/{len(manifest_json)}, expected 176/176"
    )
mc_by = {r["file"]: r for r in manifest_csv}
mj_by = {r["file"]: r for r in manifest_json}
actual = {str(p.relative_to(ROOT)) for p in subjects + versions}
if set(mc_by) != actual:
    fail(
        f"manifest CSV file set mismatch: missing={sorted(set(mc_by)-actual)}, extra={sorted(actual-set(mc_by))}"
    )
if set(mj_by) != actual:
    fail("manifest JSON file set differs from raw archive")

kind_count = defaultdict(int)
pla_count = defaultdict(int)
for rel, row in mc_by.items():
    p = ROOT / rel
    kind_count[row["kind"]] += 1
    if not p.exists():
        continue
    if int(row["size"]) != p.stat().st_size:
        fail(f"{rel}: size mismatch")
    if row["sha256"] != sha256(p):
        fail(f"{rel}: SHA-256 mismatch")
    actual_pla = b"PLA88" in p.read_bytes()
    declared = row["pla88"].lower() == "true"
    if actual_pla != declared:
        fail(f"{rel}: PLA88 manifest={declared}, actual={actual_pla}")
    if declared:
        pla_count[row["kind"]] += 1
    jr = mj_by[rel]
    for key in ("kind", "code", "version", "url", "file", "sha256"):
        if str(jr.get(key, "")) != str(row.get(key, "")):
            fail(f"{rel}: CSV/JSON manifest mismatch in {key}")
    if int(jr["size"]) != int(row["size"]) or bool(jr["pla88"]) != declared:
        fail(f"{rel}: CSV/JSON manifest mismatch in size/pla88")
    q = parse_qs(urlparse(row["url"]).query)
    if row["kind"] == "subject":
        if q.get("subject", [""])[0] != row["code"] or row["version"]:
            fail(f"{rel}: malformed subject manifest identity")
    elif row["kind"] == "version":
        if q.get("version", [""])[0] != row["version"]:
            fail(f"{rel}: malformed version manifest identity")
        if row["version"] not in p.read_text(encoding="utf-8", errors="replace"):
            fail(f"{rel}: version identifier absent from archived HTML")

if dict(kind_count) != {"subject": 54, "version": 122}:
    fail(f"manifest kind counts={dict(kind_count)}")
if pla_count.get("subject", 0) != 0 or pla_count.get("version", 0) != 106:
    fail(f"manifest PLA88 counts={dict(pla_count)}, expected subject=0/version=106")
note("raw archive: 54 + 122 files; both manifests match files, identities, sizes and SHA-256")

# 2) Sources and official exports
all_summary = parse_summary(ROOT / "sources/subject_list_vsechny_summary.txt")
valid_summary = parse_summary(ROOT / "sources/subject_list_platne_summary.txt")
subject_codes = {p.stem.removeprefix("subject_") for p in subjects}
if len(all_summary) != 54 or set(all_summary) != subject_codes:
    fail("official all-subject summary != 54 archived subject codes")
if len(valid_summary) != 14:
    fail(f"official current/future summary count={len(valid_summary)}, expected 14")
url_text = (ROOT / "sources/Vsechny-predmety.txt").read_text(encoding="utf-8")
url_codes = re.findall(r"[?&]subject=(\d{3,4}-\d{4})", url_text)
if len(url_codes) != 54 or set(url_codes) != subject_codes:
    fail(f"Vsechny-predmety.txt code set/count mismatch: {len(url_codes)}")

known_hashes = {
    "Vsechny-predmety.txt": "30a5238b442d36a9ff787e260571346f2b8634e012d43a2c33df42073eca74cd",
    "official-edison-exports/subject_list_platne.pdf": "c039116a78a8fcd888f9c39f154bc2b2d4b485a3cd23cf1aabef48606719efea",
    "official-edison-exports/subject_list_platne.xls": "d00496f926f53ca6d826d3cc2969b93222b2236ba4a82841c532ace51d45f13f",
    "official-edison-exports/subject_list_vsechny.pdf": "7dc3d38037927e3ebcbc563100ed4c75211f249fed40d7a56a898f51a3e5c4b1",
    "official-edison-exports/subject_list_vsechny.xls": "7b4c0cbcbc915232c353223ee3ddc1a24ffe1620c747958b65a107e8481b8558",
}
listed_hashes = {}
for line in (ROOT / "sources/source-files.sha256").read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, rel = line.split(None, 1)
        listed_hashes[rel.strip()] = digest
if listed_hashes != known_hashes:
    fail(f"source-files.sha256 entries differ from canonical set: {listed_hashes}")
for rel, digest in known_hashes.items():
    p = ROOT / "sources" / rel
    if not p.exists():
        fail(f"missing source input: sources/{rel}")
    elif sha256(p) != digest:
        fail(f"sources/{rel}: SHA-256 mismatch")
note("source inputs: 54 URL list + 14/54 summaries + all five canonical SHA-256 values verified")

# 3) data.js and verified CSV
m = re.fullmatch(
    r"\s*window\.PLACHA_DATA\s*=\s*(\[.*\])\s*;?\s*",
    (ROOT / "data.js").read_text(encoding="utf-8"),
    re.S,
)
if not m:
    fail("data.js unexpected format")
    data = []
else:
    data = json.loads(m.group(1))
with (ROOT / "Placha_versions_verified.csv").open(encoding="utf-8", newline="") as f:
    verified = list(csv.DictReader(f))
if len(data) != 106 or len(verified) != 106:
    fail(f"data/CSV row counts={len(data)}/{len(verified)}, expected 106/106")
if len({r[0] for r in data}) != 106 or len({r["version"] for r in verified}) != 106:
    fail("duplicate version IDs in data layer")
data_by_v = {r[0]: r for r in data}
csv_by_v = {r["version"]: r for r in verified}
if set(data_by_v) != set(csv_by_v):
    fail("data.js and verified CSV version sets differ")

raw_meta = {}
names_by_code = defaultdict(set)
for v, d in data_by_v.items():
    c = csv_by_v[v]
    code = v.split("/")[0]
    names_by_code[code].add(d[1])
    expected = {
        "code": code,
        "name": d[1],
        "introduced": d[2],
        "cancelled": d[3],
        "valid_or_future_export": str(d[4]),
        "focus_2025_2026": str(d[5]),
        "sha256": d[6],
    }
    for key, val in expected.items():
        if c[key] != val:
            fail(f"{v}: data.js/CSV mismatch in {key}: {c[key]!r}!={val!r}")
    rel = f'archive/versions/version_{v.replace("/", "_")}.html'
    if c["offline_file"] != rel or not (ROOT / rel).exists():
        fail(f"{v}: invalid offline_file")
    if parse_qs(urlparse(c["edison_url"]).query).get("version", [""])[0] != v:
        fail(f"{v}: invalid Edison URL")
    if mc_by[rel]["sha256"] != d[6] or mc_by[rel]["pla88"].lower() != "true":
        fail(f"{v}: data not backed by PLA88 manifest row")
    meta = version_meta(ROOT / rel)
    raw_meta[v] = meta
    if not meta["role"]:
        fail(f"{v}: PLA88 role cannot be parsed from raw HTML")
    if c["role_PLA88"] != meta["role"]:
        fail(f"{v}: CSV role={c['role_PLA88']!r}, raw role={meta['role']!r}")
    raw_version_name = page_name(ROOT / rel, v)
    if raw_version_name != d[1]:
        fail(f"{v}: data name={d[1]!r}, raw version name={raw_version_name!r}")

source_name_differences = {}
for code, names in names_by_code.items():
    if len(names) != 1:
        fail(f"{code}: multiple names in data.js: {sorted(names)}")
        continue
    data_name = next(iter(names))
    raw_subject_name = page_name(ROOT / f"archive/subjects/subject_{code}.html", code)
    if raw_subject_name != data_name:
        fail(f"{code}: data name={data_name!r}, raw subject name={raw_subject_name!r}")
    source_name = all_summary.get(code)
    if source_name != data_name:
        source_name_differences[code] = (source_name, data_name)

if source_name_differences != KNOWN_NAME_DIFFERENCES:
    fail(
        f"source-name differences changed: actual={source_name_differences}, expected={KNOWN_NAME_DIFFERENCES}"
    )
discrepancy_doc = (ROOT / "archive/source-discrepancies.md").read_text(encoding="utf-8")
for code, (export_name, raw_name) in KNOWN_NAME_DIFFERENCES.items():
    for token in (code, export_name, raw_name):
        if token not in discrepancy_doc:
            fail(f"source-discrepancies.md missing documented token {token!r}")

valid_codes = {r[0].split("/")[0] for r in data if r[4]}
if valid_codes != set(valid_summary):
    fail(
        f"valid/current code set differs from official export: data-only={sorted(valid_codes-set(valid_summary))}, source-only={sorted(set(valid_summary)-valid_codes)}"
    )
focus = []
for r in data:
    v, _, intro, cancel, valid, flag, _ = r
    intro_year = int(intro.split("/")[0]) if intro else 9999
    expected_focus = bool(valid) and (
        cancel == "2025/2026" or (not cancel and intro_year <= 2025)
    )
    if bool(flag) != expected_focus:
        fail(f"{v}: focus flag={flag}, rule={int(expected_focus)}")
    if flag:
        focus.append(r)
if len(focus) != 28 or len({r[0].split("/")[0] for r in focus}) != 14:
    fail("focus slice != 28 versions / 14 subjects")
note(
    "data layer: 106 versions; names/roles/URLs/hashes/focus match raw evidence; one documented Edison source-name discrepancy"
)

# 4) Conservative generation model used by the UI
by_code = defaultdict(list)
for r in data:
    by_code[r[0].split("/")[0]].append(r)
pairs = []
singles = []
generation_membership = {}
multiform = sum(1 for meta in raw_meta.values() if len(meta["forms"]) > 1)
for code, rows in by_code.items():
    buckets = defaultdict(list)
    for r in rows:
        meta = raw_meta[r[0]]
        key = (r[2], r[3], str(meta["credits"]), full_form_sig(meta))
        buckets[key].append(r[0])
    generation_no = 0
    for key, items in sorted(buckets.items(), key=lambda kv: (kv[0][0], sorted(kv[1])[0])):
        items = sorted(items)
        langs = [norm_lang(raw_meta[v]["language"]) for v in items]
        if len(items) == 2 and set(langs) == {"CZ", "EN"}:
            groups_here = [items]
            pairs.append(tuple(items))
        else:
            groups_here = [[v] for v in items]
            singles.extend(items)
        for group in groups_here:
            for v in group:
                generation_membership[v] = (code, generation_no)
            generation_no += 1

if generation_membership.get("9360-0120/02") != generation_membership.get("9360-0120/04"):
    fail("9360-0120/02 + /04 should form one CZ/EN generation")
if generation_membership.get("9360-0120/03") != generation_membership.get("9360-0120/05"):
    fail("9360-0120/03 + /05 should form one CZ/EN generation")
if generation_membership.get("9360-0131/02") == generation_membership.get("9360-0131/04"):
    fail("9360-0131/02 + /04 are both CZ and must remain separate")

index = (ROOT / "index.html").read_text(encoding="utf-8")
for marker in (
    "function formSignature",
    "function buildGenerations",
    "m.forms.map",
    "items.length===2",
    "langs.includes('CZ')",
    "langs.includes('EN')",
):
    if marker not in index:
        fail(f"index.html missing conservative grouping marker: {marker}")
note(
    f"UI grouping: {len(pairs)} unambiguous CZ/EN pairs, {len(singles)} standalone variants; {multiform} versions preserve multiple study forms"
)

# 5) Main web syntax, links and project hygiene
inline_scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', index, re.S)
for i, js in enumerate(inline_scripts, 1):
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
        f.write(js)
        tmp = f.name
    proc = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    Path(tmp).unlink(missing_ok=True)
    if proc.returncode:
        fail(f"index.html inline JavaScript #{i} syntax error: {proc.stderr.strip()}")

for page in (ROOT / "index.html", ROOT / "archive/index.html"):
    text = page.read_text(encoding="utf-8", errors="replace")
    if "drive.google.com" in text:
        fail(f"stale Google Drive URL in {page.relative_to(ROOT)}")
    for href in re.findall(r'href="([^"]+)"', text):
        if href.startswith(("http://", "https://", "#")) or "${" in href:
            continue
        target = (page.parent / href.split("#")[0].split("?")[0]).resolve()
        if href and not target.exists():
            fail(f"{page.relative_to(ROOT)} broken local href: {href}")

for p in [
    ROOT / "README.md",
    ROOT / "data.js",
    ROOT / "Placha_versions_verified.csv",
    *list((ROOT / "sources").glob("*.txt")),
    *list((ROOT / "sources").glob("*.sha256")),
    *list((ROOT / "sources/official-edison-exports").glob("*.md")),
]:
    if "drive.google.com" in p.read_text(encoding="utf-8", errors="replace"):
        fail(f"stale Google Drive URL in {p.relative_to(ROOT)}")

archive_index = (ROOT / "archive/index.html").read_text(encoding="utf-8", errors="replace")
for p in subjects + versions:
    rel = str(p.relative_to(ROOT / "archive"))
    if rel not in archive_index:
        fail(f"archive/index.html does not reference {rel}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for token in ("54 hlavních", "122 stránek", "106 verzí", "28 verzí / 14 předmětů"):
    if token not in readme:
        fail(f"README missing expected summary token: {token}")

complete = dict(
    line.split("=", 1)
    for line in (ROOT / "archive/.complete").read_text().splitlines()
    if "=" in line
)
report = dict(
    line.split("=", 1)
    for line in (ROOT / "archive/report-build.txt").read_text().splitlines()
    if "=" in line
)
if complete != {"subjects": "54", "versions": "122", "pla88_versions": "106"}:
    fail(f"archive/.complete inconsistent: {complete}")
for key, value in {
    "versions_with_PLA88": "106",
    "subjects_with_PLA88": "54",
    "focus_2025_2026_versions": "28",
    "focus_2025_2026_subjects": "14",
    "new_vs_original": "9360-0125/02",
}.items():
    if report.get(key) != value:
        fail(f"archive/report-build.txt {key}={report.get(key)!r}, expected {value!r}")
if (ROOT / ".pages-enabled").exists():
    fail(".pages-enabled stale trigger still exists")

workflow_names = sorted(p.name for p in (ROOT / ".github/workflows").glob("*.yml"))
if workflow_names != ["consistency.yml", "pages.yml"]:
    fail(f"unexpected workflow set: {workflow_names}")
note(
    "web/project hygiene: JavaScript parses, links resolve, archive index covers all raw pages, no Drive URLs or temporary workflow remains"
)

print("=== PROJECT CONSISTENCY AUDIT ===")
for x in notes:
    print("OK   ", x)
for x in errors:
    print("FAIL ", x)
print(f"\nSUMMARY: {len(errors)} failures, {len(notes)} check groups")
if errors:
    sys.exit(1)

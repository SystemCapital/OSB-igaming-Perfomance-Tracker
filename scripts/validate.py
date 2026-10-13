#!/usr/bin/env python3
"""Validate the tracker repository. Run from anywhere:  python scripts/validate.py

Checks
  1. every data/*.json named in data/schema.json exists and parses
  2. each dataset matches the shape recorded at conversion (row length, required keys,
     source lists with the minimum number of [label, https-url] pairs, ISO dates, links)
  3. data/meta.json has a snapshot date and label
  4. the page scripts in index.html parse (needs node; skipped if absent)
  5. the ready-to-open single-file build contains exactly the current data (i.e. it was rebuilt)
  6. the single-file build runs in a simulated browser without new errors (needs node)
Enum-like fields that gain a new value only produce a warning.
Exit 0 = passed, 1 = problems found.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NODE = shutil.which("node")
ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def is_url(u):
    return isinstance(u, str) and u.startswith(("http://", "https://"))


def is_pair(x):
    return isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and is_url(x[1])


def check_field(where, val, f, errors, warnings):
    role = f.get("role")
    if role == "sources":
        if not isinstance(val, list):
            errors.append(f"{where}: sources must be a list of [label, url]")
            return
        bad = [s for s in val if not is_pair(s)]
        if bad:
            errors.append(f"{where}: each source must be [label, http(s) url], got {str(bad[0])[:120]}")
        if len(val) < f.get("min", 1):
            errors.append(f"{where}: has {len(val)} source(s); needs at least {f.get('min', 1)}")
    elif role == "link":
        if not is_pair(val):
            errors.append(f"{where}: must be [label, http(s) url]")
    elif role == "isodate":
        if not (isinstance(val, str) and ISO.match(val)):
            errors.append(f"{where}: must be an ISO date YYYY-MM or YYYY-MM-DD, got {val!r}")
    elif role == "enum":
        if val not in f.get("values", []):
            warnings.append(f"{where}: new value {val!r} (seen at conversion: {', '.join(map(str, f['values']))}) - fine if intended")


def check_dataset(name, v, sch, errors, warnings):
    kind = sch.get("kind")
    if kind in ("rows", "records", "list"):
        if not isinstance(v, list):
            errors.append(f"{name}: must be a list")
            return
        if len(v) < sch.get("min_rows", 0):
            errors.append(f"{name}: is empty")
    if kind == "rows":
        allowed = [sch["row_length"]] if sch.get("row_length") else sch.get("row_lengths", [])
        for i, r in enumerate(v):
            where = f"{name}[{i}] ({str(r[0])[:40] if isinstance(r, list) and r else '?'})"
            if not isinstance(r, list):
                errors.append(f"{where}: each row must be a list")
                continue
            if allowed and len(r) not in allowed:
                errors.append(f"{where}: has {len(r)} fields, expected {' or '.join(map(str, allowed))}")
                continue
            for k, f in sch.get("fields", {}).items():
                if int(k) < len(r):
                    check_field(f"{where} field {k}", r[int(k)], f, errors, warnings)
    elif kind == "records":
        req = set(sch.get("required_keys", []))
        for i, r in enumerate(v):
            where = f"{name}[{i}]"
            if not isinstance(r, dict):
                errors.append(f"{where}: each item must be an object")
                continue
            missing = req - set(r)
            if missing:
                errors.append(f"{where}: missing keys {sorted(missing)}")
            for k, f in sch.get("fields", {}).items():
                if k in r:
                    check_field(f"{where}.{k}", r[k], f, errors, warnings)
    elif kind == "object":
        if not isinstance(v, dict):
            errors.append(f"{name}: must be an object")
            return
        missing = set(sch.get("required_keys", [])) - set(v)
        if missing:
            errors.append(f"{name}: missing top-level keys {sorted(missing)}")


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def page_scripts(html):
    out = []
    for m in re.finditer(r"<script\b([^>]*)>([\s\S]*?)</script\s*>", html, re.I):
        a = m.group(1) or ""
        if "data-tracker-app" in a or "data-tracker-loader" in a:
            out.append(m.group(2))
    return out


def node_check(code):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(code)
    r = subprocess.run([NODE, "--check", f.name], capture_output=True, text=True)
    Path(f.name).unlink(missing_ok=True)
    return r


def main():
    errors, warnings = [], []
    try:
        schema = json.loads((DATA / "schema.json").read_text(encoding="utf-8"))
    except Exception as e:
        print(f"VALIDATION FAILED - cannot read data/schema.json: {e}")
        sys.exit(1)
    data = {}
    for name in list(schema["datasets"]) + ["meta"]:
        try:
            data[name] = load(name)
        except FileNotFoundError:
            errors.append(f"data/{name}.json is missing")
        except json.JSONDecodeError as e:
            errors.append(f"data/{name}.json is not valid JSON: {e}")
    for name, sch in schema["datasets"].items():
        if name in data:
            check_dataset(name, data[name], sch, errors, warnings)
    meta = data.get("meta", {})
    if not (isinstance(meta, dict) and ISO.match(str(meta.get("snapshot_date", ""))) and meta.get("snapshot_label")):
        errors.append("data/meta.json needs snapshot_date (YYYY-MM-DD) and snapshot_label - run scripts/set_snapshot.py")

    index = ROOT / "index.html"
    if not index.exists():
        errors.append("index.html is missing")
    elif NODE:
        for k, code in enumerate(page_scripts(index.read_text(encoding="utf-8"))):
            r = node_check(code)
            if r.returncode != 0:
                errors.append(f"index.html script block #{k + 1} has a JavaScript syntax error:\n{r.stderr.strip()[-600:]}")
    else:
        warnings.append("node not found - skipped page script and render checks")

    standalone = ROOT / meta.get("standalone_file", "dashboard.html") if isinstance(meta, dict) else None
    if not errors and standalone is not None:
        if not standalone.exists():
            errors.append(f"{standalone.name} is missing - run: python scripts/build_standalone.py")
        else:
            html = standalone.read_text(encoding="utf-8")
            mark = "window.__TRACKER_EMBED__="
            i = html.find(mark)
            j = html.find(";</script>", i)
            try:
                embedded = json.loads(html[i + len(mark):j]) if i >= 0 else None
            except json.JSONDecodeError:
                embedded = None
            if embedded is None:
                errors.append(f"{standalone.name} has no readable embedded data - run: python scripts/build_standalone.py")
            else:
                stale = [n for n, v in data.items() if embedded.get(n) != v]
                if stale:
                    errors.append(f"{standalone.name} is out of date ({', '.join(stale)} changed) - run: python scripts/build_standalone.py")
            if not errors and NODE and (ROOT / "scripts" / "render_check.js").exists():
                r = subprocess.run([NODE, str(ROOT / "scripts" / "render_check.js"), str(standalone)], capture_output=True, text=True, timeout=300)
                try:
                    res = json.loads(r.stdout)
                    new = sorted(set(res["errors"]) - set(schema.get("baseline_render_errors", [])))
                    if new:
                        errors.append(f"{standalone.name} throws errors when run:\n    " + "\n    ".join(new[:8]))
                    elif not res["writes"]:
                        errors.append(f"{standalone.name} rendered nothing in the simulated browser")
                except Exception:
                    errors.append(f"render check could not run: {(r.stderr or r.stdout)[-400:]}")

    counts = ", ".join(f"{n} {len(v)}" for n, v in data.items() if isinstance(v, (list, dict)) and n != "meta")
    print(f"Datasets: {counts}")
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        print(f"\nVALIDATION FAILED - {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()

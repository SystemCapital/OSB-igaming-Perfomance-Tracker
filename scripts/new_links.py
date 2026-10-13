#!/usr/bin/env python3
"""List the source URLs added to data/*.json since a git revision, and optionally check them.

Use it before committing a data update, so that no invented or broken link slips in:
    python scripts/new_links.py              # URLs added vs the last commit (HEAD)
    python scripts/new_links.py --check      # ...and request each one, report failures
    python scripts/new_links.py --since origin/main --check

Note: some news sites block automated requests (HTTP 401/403/429). Those are reported as
"blocked" rather than "broken"; confirm them another way (e.g. your web search results).
Checking needs outbound internet access (a "Full" or "Custom" network environment).
Exit codes: 0 = all fine, 1 = some links broken/unreachable, 2 = no link reachable at all
(network unavailable - the result says nothing about the links).
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; tracker-link-check/1.0)"


def urls_in(obj):
    out = set()
    if isinstance(obj, str) and obj.startswith(("http://", "https://")):
        out.add(obj)
    elif isinstance(obj, list):
        for x in obj:
            out |= urls_in(x)
    elif isinstance(obj, dict):
        for x in obj.values():
            out |= urls_in(x)
    return out


def urls_at(rev):
    found = set()
    for p in sorted((ROOT / "data").glob("*.json")):
        rel = p.relative_to(ROOT).as_posix()
        if rev is None:
            text = p.read_text(encoding="utf-8")
        else:
            r = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                continue  # file did not exist at that revision
            text = r.stdout
        found |= urls_in(json.loads(text))
    return found


def check(url):
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return "ok", r.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 400, 501):
                continue  # some servers reject HEAD; retry with GET
            return ("blocked" if e.code in (401, 403, 429) else "broken"), e.code
        except Exception as e:
            if method == "HEAD":
                continue
            return "error", e.__class__.__name__
    return "error", "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="HEAD", help="git revision to compare against (default HEAD)")
    ap.add_argument("--check", action="store_true", help="request each new URL")
    a = ap.parse_args()

    new = sorted(urls_at(None) - urls_at(a.since))
    if not new:
        print(f"No new source URLs since {a.since}.")
        return
    print(f"{len(new)} new source URL(s) since {a.since}:")
    bad = 0
    results = []
    for u in new:
        if a.check:
            status, code = check(u)
            results.append(status)
            bad += status in ("broken", "error")
            print(f"  [{status} {code}] {u}")
        else:
            print(f"  {u}")
    if a.check and new and len(results) == len(new) and all(st == "error" for st in results):
        print("\nNO LINK COULD BE REACHED - the network is probably unavailable (e.g. a 'Trusted' or 'None'"
              "\nenvironment). These results say nothing about the links themselves. Do NOT remove links on"
              "\nthis basis; keep only URLs that came from your search results, and note 'links unchecked' in the log.")
        sys.exit(2)
    if a.check and bad:
        print(f"\n{bad} link(s) broken or unreachable - verify or replace them before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()

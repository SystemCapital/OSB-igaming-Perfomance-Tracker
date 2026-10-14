#!/usr/bin/env python3
"""Build the ready-to-open single-file dashboard (name in data/meta.json "standalone_file").

index.html loads data/*.json and vendor/* at runtime, which needs a web server. This bakes the
data and every vendored library/stylesheet into ONE file that opens by double-click, works
offline, can be emailed, and can be published as a Claude artifact.

Run after every data or page change (scripts/validate.py fails if you forget):
    python scripts/build_standalone.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main():
    schema = json.loads((DATA / "schema.json").read_text(encoding="utf-8"))
    names = list(schema["datasets"]) + ["meta"]
    data = {n: json.loads((DATA / f"{n}.json").read_text(encoding="utf-8")) for n in names}
    out = ROOT / data["meta"].get("standalone_file", "dashboard.html")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    def inline_js(m):
        p = ROOT / m.group(1)
        lib = p.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f'<script data-vendor="{p.name}">{lib}</script>'

    def inline_css(m):
        p = ROOT / m.group(1)
        return f'<style data-vendor="{p.name}">{p.read_text(encoding="utf-8")}</style>'

    html = re.sub(r'<script src="(vendor/[^"]+)" data-vendor="[^"]*"></script>', inline_js, html)
    html = re.sub(r'<link rel="stylesheet" href="(vendor/[^"]+)" data-vendor="[^"]*">', inline_css, html)
    i = html.find("<script data-tracker-loader>")
    if i < 0:
        raise SystemExit("index.html has no <script data-tracker-loader> block")
    html = html[:i] + f"<script>window.__TRACKER_EMBED__={blob};</script>\n" + html[i:]
    # Run the page code as ordinary inline scripts. index.html keeps it in text/plain blocks that its
    # loader injects once data/*.json has loaded, but sandboxes with a nonce-based Content-Security-
    # Policy (such as Claude artifacts) can refuse injected scripts, leaving an empty page. Here the data is
    # already embedded, so a two-line boot script replaces the loader.
    boot = ('<script data-tracker-boot>window.__TRACKER_DATA__=window.__TRACKER_EMBED__;'
            '(function(m){if(!m||!m.snapshot_label)return;var e=document.querySelectorAll(".snapdate");'
            'for(var i=0;i<e.length;i++)e[i].textContent=m.snapshot_label;})(window.__TRACKER_DATA__.meta);</script>')
    html, n = re.subn(r"<script data-tracker-loader>[\s\S]*?</script>", lambda _: boot, html, count=1)
    html, k = re.subn(r'<script type="text/plain" data-tracker-app>', "<script data-tracker-main>", html)
    if n != 1 or not k:
        raise SystemExit("index.html loader or data-tracker-app blocks not found")
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out.name} ({out.stat().st_size:,} bytes) - data and libraries embedded, works offline")


if __name__ == "__main__":
    main()

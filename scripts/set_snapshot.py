#!/usr/bin/env python3
"""Set the tracker's snapshot date (data/meta.json) to today, or to a given date.

    python scripts/set_snapshot.py               # today (time zone: DASHBOARD_TZ, default Australia/Sydney)
    python scripts/set_snapshot.py 2026-10-12    # a specific date
The label keeps the date style the original page used (e.g. "October 5, 2026").
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

META = Path(__file__).resolve().parent.parent / "data" / "meta.json"


def label(d, fmt):
    return {"long": f"{d.strftime('%B')} {d.day}, {d.year}", "short": f"{d.strftime('%b')} {d.day}, {d.year}",
            "dmy": f"{d.day} {d.strftime('%B')} {d.year}", "iso": d.isoformat()}.get(fmt, f"{d.strftime('%B')} {d.day}, {d.year}")


def main():
    if len(sys.argv) > 1:
        d = dt.date.fromisoformat(sys.argv[1])
    else:
        try:
            from zoneinfo import ZoneInfo
            d = dt.datetime.now(ZoneInfo(os.environ.get("DASHBOARD_TZ", "Australia/Sydney"))).date()
        except Exception:
            d = dt.date.today()
    meta = json.loads(META.read_text(encoding="utf-8"))
    meta["snapshot_date"] = d.isoformat()
    meta["snapshot_label"] = label(d, meta.get("label_format", "long"))
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Snapshot date set to {meta['snapshot_label']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""CLI: sourcea-boot — PASS or BLOCK before agent execution."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sourcea_boot.runner import run_boot


def main() -> int:
    ap = argparse.ArgumentParser(
        description="sourcea-boot — four checks, PASS or BLOCK, writes BOOT_REPORT.json",
    )
    ap.add_argument("--project-root", type=Path, default=None, help="Project directory (default: cwd)")
    ap.add_argument("--in-gate", action="store_true", help="Called from session gate — relax receipt staleness")
    ap.add_argument("--no-write", action="store_true", help="Do not write BOOT_REPORT.json")
    ap.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    args = ap.parse_args()

    row = run_boot(args.project_root, in_gate=args.in_gate, write_report=not args.no_write)
    if args.json:
        print(json.dumps(row, indent=2))
    else:
        print(f"SOURCEA_BOOT {row['verdict']} ok={row['ok']}")
        for c in row["checks"]:
            mark = "PASS" if c.get("ok") else "FAIL"
            print(f"  [{mark}] {c.get('name')}: {c.get('reason')}")
        print(f"REPORT={row.get('report_file')}")
    return 0 if row.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Boot runner — one command in, BOOT_REPORT.json out."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sourcea_boot.checks import (
    REPORT_NAME,
    check_policy_version,
    check_provider,
    check_queue_truth,
    check_receipt_fresh,
    detect_sourcea_factory,
    load_config,
)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_boot(
    project_root: Path | None = None,
    *,
    in_gate: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    root = (project_root or Path.cwd()).resolve()
    cfg = load_config(root)
    factory = detect_sourcea_factory(root)

    checks = [
        check_policy_version(root, cfg),
        check_provider(root, cfg),
        check_receipt_fresh(root, cfg, in_gate=in_gate),
        check_queue_truth(root, cfg),
    ]
    ok = all(c.get("ok") for c in checks)
    blockers = [c["reason"] for c in checks if not c.get("ok")]

    row: dict[str, Any] = {
        "schema": "sourcea-boot-v1",
        "package": "sourcea-boot",
        "version": "0.1.0",
        "at": _now(),
        "verdict": "PASS" if ok else "BLOCK",
        "ok": ok,
        "project_root": str(root),
        "factory_mode": bool(factory),
        "factory_root": str(factory) if factory else None,
        "checks": checks,
        "blockers": blockers,
        "founder_line": (
            "SOURCEA BOOT PASS — safe to execute"
            if ok
            else f"SOURCEA BOOT BLOCK — {' · '.join(blockers[:2])}"
        ),
        "report_file": str(root / REPORT_NAME),
    }

    if write_report:
        report_path = root / REPORT_NAME
        report_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
        if factory:
            sina_receipt = Path.home() / ".sina" / "critic-boot-v1.json"
            sina_receipt.parent.mkdir(parents=True, exist_ok=True)
            legacy = {
                "schema": "critic-boot-v1",
                "at": row["at"],
                "verdict": row["verdict"],
                "ok": ok,
                "checks": checks,
                "blockers": blockers,
                "founder_line": row["founder_line"],
                "law": "sourcea-boot package",
                "receipt_path": str(sina_receipt),
            }
            sina_receipt.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")

    return row

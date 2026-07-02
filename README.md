# sourcea-boot

[![validate-sourcea-boot](https://github.com/kazemnezhadsina144-dot/sourcea-boot/actions/workflows/validate-sourcea-boot-v1.yml/badge.svg)](https://github.com/kazemnezhadsina144-dot/sourcea-boot/actions/workflows/validate-sourcea-boot-v1.yml)

**One command. PASS or BLOCK before your agents run.**

## Run in 5 minutes

```bash
git clone https://github.com/kazemnezhadsina144-dot/sourcea-boot.git
cd sourcea-boot
pip install -e .
sourcea-boot --json
```

PyPI (Phase 0b — trusted publishing prepared, not live yet):

```bash
# pip install sourcea-boot   # not on PyPI yet — clone + editable install above
sourcea-boot --json
```

When published, install will be `pip install sourcea-boot` via GitHub Actions trusted publishing (no long-lived PyPI token). See `docs/PYPI_TRUSTED_PUBLISHING_SETUP.md` in this repo after export.

Writes `BOOT_REPORT.json` in the current directory. Exit code `0` = PASS, `1` = BLOCK.

Expected output:

```text
$ sourcea-boot --json
SOURCEA_BOOT PASS ok=true
  [PASS] policy_version: ...
  [PASS] provider: ...
  [PASS] receipt_fresh: ...
  [PASS] queue_truth: ...
REPORT=BOOT_REPORT.json
```

## CI validation

Factory CI runs `scripts/validate-sourcea-boot-v1.sh` — four checks, PASS/BLOCK contract, `BOOT_REPORT.json` on disk.

## What it checks

| Check | Meaning |
|-------|---------|
| `policy_version` | Project policy / SSOT file not stale vs last brief |
| `provider` | LLM embedding provider configured (no fake-green hash mode when keys exist) |
| `receipt_fresh` | Last boot/gate receipt fresh (<8h) and ok |
| `queue_truth` | Agent queue head matches inbox truth (when queue files present) |

## SourceA factory mode

When run inside a SourceA monorepo (detects `SOURCEA_UNIFIED_PORTFOLIO_COMMERCIAL_SSOT_LOCKED_v3.1.md`), runs full factory spine checks against `~/.sina/`.

## Zero config

Works in any project. Optional config: `.sourcea-boot.json` in project root.

```json
{
  "policy_file": "POLICY.md",
  "receipt_path": ".sourcea/boot-receipt.json",
  "max_receipt_age_hours": 8
}
```

## Repository

https://github.com/kazemnezhadsina144-dot/sourcea-boot

## License

MIT · [SourceA](https://sourcea.com) · hello@sourcea.app

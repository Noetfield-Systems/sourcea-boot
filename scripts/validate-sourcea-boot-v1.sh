#!/usr/bin/env bash
# Standalone public-repo validator for sourcea-boot (portable mode).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: validate-sourcea-boot-v1 — $*" >&2; exit 1; }

[[ -d "$ROOT/src/sourcea_boot" ]] || fail "missing package src/sourcea_boot"

export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
BOOT_JSON="$(python3 -m sourcea_boot.cli --json 2>/dev/null || true)"
[[ -n "$BOOT_JSON" ]] || fail "sourcea-boot produced no JSON"
printf '%s' "$BOOT_JSON" | python3 -c "
import json, sys
row = json.load(sys.stdin)
assert row.get('schema') == 'sourcea-boot-v1'
assert row.get('verdict') in ('PASS', 'BLOCK')
assert len(row.get('checks') or []) == 4
print('OK: sourcea-boot CLI · 4 checks · verdict', row.get('verdict'))
" || fail "boot CLI contract"

[[ -f BOOT_REPORT.json ]] || fail "BOOT_REPORT.json not written"
rm -f BOOT_REPORT.json

echo "OK: validate-sourcea-boot-v1 · standalone public repo"

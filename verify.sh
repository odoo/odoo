#!/usr/bin/env bash
# verify.sh <module>
# Runs pre-flight checks, lint, and tests for an Odoo module.
# Requires the odoo19 conda env and a running PostgreSQL instance.
#
# Usage:
#   ./verify.sh account
#   ./verify.sh up5_my_module

set -e

MODULE=${1:?Usage: ./verify.sh <module_name>}
ADDON_PATH="addons/$MODULE"

# ── Pre-flight ────────────────────────────────────────────────────────────────

echo "=== Pre-flight checks ==="

if ! conda run -n odoo19 python odoo-bin --version &>/dev/null; then
  echo "ERROR: conda env 'odoo19' not active or odoo-bin not found."
  echo "Run: conda activate odoo19"
  exit 1
fi
echo "  odoo-bin: ok"

if ! conda run -n odoo19 python -c "
import psycopg2, sys
try:
    psycopg2.connect(host='localhost', port=5432, user='odoo', password='odoo', dbname='odoo_dev')
except Exception as e:
    print(f'  PostgreSQL: FAIL — {e}')
    print('  See startup-readiness.md Condition 1 for setup steps.')
    sys.exit(1)
" 2>&1; then
  exit 1
fi
echo "  PostgreSQL: ok"

if [ ! -d "$ADDON_PATH" ]; then
  echo "ERROR: $ADDON_PATH does not exist"
  exit 1
fi
echo "  Module path: ok ($ADDON_PATH)"
echo ""

# ── Lint ──────────────────────────────────────────────────────────────────────

echo "=== Lint: ruff check $ADDON_PATH ==="
conda run -n odoo19 ruff check "$ADDON_PATH"
echo "Lint passed."
echo ""

# ── Tests ─────────────────────────────────────────────────────────────────────

echo "=== Tests: -i $MODULE ==="
conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i "$MODULE" \
  --log-level=test
echo "Tests passed."
echo ""

echo "=== $MODULE: all checks passed ==="

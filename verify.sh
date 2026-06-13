#!/usr/bin/env bash
# verify.sh <module>
# Three-layer verification for an Odoo module.
# Requires the odoo19 conda env and a running PostgreSQL instance.
#
# Layer 1 — Static analysis: pre-flight + ruff lint
# Layer 2 — Runtime verification: Odoo test runner
# Layer 3 — System confirmation: manual smoke test (prompted at end for up5_* modules)
#
# Usage:
#   ./verify.sh account
#   ./verify.sh up5_my_module

set -e

MODULE=${1:?Usage: ./verify.sh <module_name>}
ADDON_PATH="addons/$MODULE"

# ── Pre-flight ────────────────────────────────────────────────────────────────

echo "=== Pre-flight ==="

if ! conda run -n odoo19 python odoo-bin --version &>/dev/null; then
  echo "  FAIL: odoo-bin not found in conda env 'odoo19'."
  echo "  Fix: conda activate odoo19 && python odoo-bin --version"
  exit 1
fi
echo "  odoo-bin: ok"

if ! conda run -n odoo19 python -c "import psycopg2; psycopg2.connect(host='localhost', port=5432, user='odoo', password='odoo', dbname='odoo_dev')" 2>/dev/null; then
  echo "  FAIL: cannot connect to PostgreSQL at localhost:5432 as user 'odoo'."
  echo "  Fix: ensure PostgreSQL is running and odoo_dev database exists."
  echo "  See: startup-readiness.md Condition 1"
  exit 1
fi
echo "  PostgreSQL: ok"

if [ ! -d "$ADDON_PATH" ]; then
  echo "  FAIL: $ADDON_PATH does not exist."
  echo "  Fix: check module name spelling or run from repo root."
  exit 1
fi
echo "  Module path: ok ($ADDON_PATH)"
echo ""

# ── Layer 1: Static Analysis ───────────────────────────────────────────────────

if [[ "$MODULE" == up5_* ]]; then
  echo "=== Layer 1 — Static Analysis: ruff check $ADDON_PATH ==="
  if ! conda run -n odoo19 ruff check "$ADDON_PATH"; then
    echo ""
    echo "  FAIL: ruff lint errors above must be fixed before Layer 2."
    echo "  Fix: conda run -n odoo19 ruff check --fix $ADDON_PATH"
    exit 1
  fi
  echo "Layer 1 passed."
  echo ""
else
  echo "=== Layer 1 — Static Analysis: skipped (core Odoo module) ==="
  echo ""
fi

# ── Layer 2: Runtime Verification ─────────────────────────────────────────────

echo "=== Layer 2 — Runtime Verification: -i $MODULE ==="
if ! conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i "$MODULE" \
  --log-level=test; then
  echo ""
  echo "  FAIL: Odoo test runner exited non-zero."
  echo "  Fix: read the traceback above; check imports, model definitions, and access CSV."
  exit 1
fi
echo "Layer 2 passed."
echo ""

# ── Layer 3 reminder ─────────────────────────────────────────────────────────

if [[ "$MODULE" == up5_* ]]; then
  echo "=== Layer 3 — System Confirmation (manual) ==="
  echo "  Before marking this task 'passing', confirm in the browser:"
  echo "  1. Start server: conda run -n odoo19 python odoo-bin -c odoo.conf"
  echo "  2. Open http://localhost:8069 and log in"
  echo "  3. Install/upgrade the module and exercise the critical path"
  echo "  4. Note the result in claude-progress.md"
  echo ""
fi

echo "=== $MODULE: Layers 1+2 passed — complete Layer 3 manually before marking 'passing' ==="

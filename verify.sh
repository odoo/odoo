#!/usr/bin/env bash
# verify.sh <module>
# Runs lint + tests for an Odoo module. Requires the odoo19 conda env.
#
# Usage:
#   ./verify.sh account
#   ./verify.sh point_of_sale

set -e

MODULE=${1:?Usage: ./verify.sh <module_name>}
ADDON_PATH="addons/$MODULE"

if [ ! -d "$ADDON_PATH" ]; then
  echo "ERROR: $ADDON_PATH does not exist"
  exit 1
fi

echo "=== Lint: ruff check $ADDON_PATH ==="
conda run -n odoo19 ruff check "$ADDON_PATH"
echo "Lint passed."

echo ""
echo "=== Tests: -i $MODULE ==="
conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i "$MODULE" \
  --log-level=test
echo "Tests passed."

echo ""
echo "=== $MODULE: all checks passed ==="

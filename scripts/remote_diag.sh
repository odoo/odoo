#!/usr/bin/env bash
# Remote diagnostics: invoice_agent visibility on EC2
set +e

cd /opt/odoo || exit 1

echo "=== DATABASES ==="
DB_LIST=$(docker compose exec -T db psql -U odoo -d postgres -t -A -c \
  "SELECT datname FROM pg_database WHERE datistemplate=false AND datname NOT IN ('postgres','template1');" 2>/dev/null | tr -d '\r' | sed '/^$/d')
echo "$DB_LIST"

echo ""
echo "=== invoice_agent in ir_module_module (per DB) ==="
for DB in $DB_LIST; do
  echo "--- DB: $DB ---"
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT name, state, latest_version FROM ir_module_module WHERE name='invoice_agent';" 2>&1
  echo "  (rows above: EMPTY = not installed; state should be 'installed')"
done

echo ""
echo "=== git HEAD on server ==="
git rev-parse --abbrev-ref HEAD
git log --oneline -1

echo ""
echo "=== local __manifest__ version ==="
grep -m1 version /opt/odoo/custom_addons/invoice_agent/__manifest__.py

echo ""
echo "=== Odoo log: last 300 lines, grep relevant ==="
docker compose logs --tail=300 odoo 2>&1 | grep -iE 'error|critical|traceback|invoice_agent|loading module' | tail -50

echo ""
echo "=== modules available to Odoo (addons path) ==="
docker compose exec -T odoo odoo --version 2>/dev/null
docker compose exec -T odoo odoo --help 2>/dev/null | grep -i addons-path | head -2

echo ""
echo "DONE"

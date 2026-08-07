#!/usr/bin/env bash
# Pre-flight: verify invoice_agent can install cleanly on the odoo DB
set +e
cd /opt/odoo || exit 1

echo "=== dependencies installed? (odoo DB) ==="
docker compose exec -T db psql -U odoo -d odoo -c \
  "SELECT name, state FROM ir_module_module WHERE name IN ('account','sale','base_automation','base') ORDER BY name;"

echo ""
echo "=== module directory (server) ==="
ls -la custom_addons/invoice_agent/

echo ""
echo "=== requirements.txt (server copy) ==="
cat custom_addons/invoice_agent/requirements.txt 2>/dev/null || echo "(no requirements.txt)"

echo ""
echo "=== hooks.py ==="
cat custom_addons/invoice_agent/hooks.py

echo ""
echo "=== disk space ==="
df -h / | tail -1

echo ""
echo "=== docker memory ==="
free -h | head -2

echo "DONE"

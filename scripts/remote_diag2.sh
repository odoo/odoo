#!/usr/bin/env bash
# Remote diagnostics part 2: invoice_agent never-installed check
set +e
cd /opt/odoo || exit 1

echo "=== .env POSTGRES_DB / DOMAIN ==="
grep -E '^POSTGRES_DB=|^DOMAIN=' .env

echo ""
echo "=== module row (odoo DB) ==="
docker compose exec -T db psql -U odoo -d odoo -c \
  "SELECT name,state,latest_version,create_date,write_date FROM ir_module_module WHERE name='invoice_agent';"

echo ""
echo "=== module row (all DB) ==="
docker compose exec -T db psql -U odoo -d all -c \
  "SELECT name,state,latest_version,create_date,write_date FROM ir_module_module WHERE name='invoice_agent';"

echo ""
echo "=== invoice_agent tables (odoo DB) ==="
docker compose exec -T db psql -U odoo -d odoo -t -c \
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE '%invoice%agent%';"

echo ""
echo "=== invoice_agent tables (all DB) ==="
docker compose exec -T db psql -U odoo -d all -t -c \
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE '%invoice%agent%';"

echo ""
echo "=== which DB does odoo serve? grep db_name in logs ==="
docker compose logs --tail=500 odoo 2>&1 | grep -oiE "addons-path[^\"]*|database: [a-z_]+|db_name[^,]*" | sort -u | head -10

echo ""
echo "=== odoo command line (actual process) ==="
docker inspect odoo-odoo-1 --format '{{.Args}}' 2>/dev/null

echo "DONE"

#!/usr/bin/env bash
# Identify which DB is the real production database
set +e
cd /opt/odoo || exit 1

for DB in odoo all; do
  echo "===== DB: $DB ====="
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT 'tables', count(*) FROM pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'ir_%';"
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT 'users', count(*) FROM res_users WHERE active IS NULL OR active;" 2>/dev/null
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT 'invoice_moves', count(*) FROM account_move WHERE move_type IN ('out_invoice','out_refund') AND state IN ('posted','draft');" 2>/dev/null
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT 'web.base.url', value FROM ir_config_parameter WHERE key='web.base.url';" 2>/dev/null
  docker compose exec -T db psql -U odoo -d "$DB" -t -c \
    "SELECT 'companies', name FROM res_company LIMIT 3;" 2>/dev/null
  echo ""
done

echo "=== Odoo boot log: which DB loaded at startup? ==="
docker compose logs odoo 2>&1 | grep -iE "loading module|odoo.modules.loading|database:" | head -20
echo "DONE"

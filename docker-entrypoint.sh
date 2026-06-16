#!/usr/bin/env bash
set -e

DB_HOST="${ODOO_DB_HOST:-db}"
DB_PORT="${ODOO_DB_PORT:-5432}"
DB_USER="${ODOO_DB_USER:-odoo}"
DB_PASSWORD="${ODOO_DB_PASSWORD:-odoo}"

cat > /etc/odoo/odoo.conf <<EOF
[options]
admin_passwd = ${ODOO_ADMIN_PASSWORD:-admin}
addons_path = ${ODOO_ADDONS_PATH:-/mnt/extra-addons,/mnt/extra-addons/KSW}
db_host = ${DB_HOST}
db_port = ${DB_PORT}
db_user = ${DB_USER}
db_password = ${DB_PASSWORD}
dbfilter = ${ODOO_DBFILTER:-.*}
proxy_mode = ${ODOO_PROXY_MODE:-False}
xmlrpc_port = ${ODOO_XMLRPC_PORT:-8069}
longpolling_port = ${ODOO_LONGPOLLING_PORT:-8072}
log_level = ${ODOO_LOG_LEVEL:-info}
workers = ${ODOO_WORKERS:-0}
max_cron_threads = ${ODOO_MAX_CRON_THREADS:-1}
data_dir = /var/lib/odoo
EOF

if [ -n "${SMTP_SERVER:-}" ]; then
  cat >> /etc/odoo/odoo.conf <<EOF
smtp_server = ${SMTP_SERVER}
smtp_port = ${SMTP_PORT:-25}
smtp_user = ${SMTP_USER:-}
smtp_password = ${SMTP_PASSWORD:-}
smtp_security = ${SMTP_SECURITY:-starttls}
EOF
fi

if [ -n "${DB_NAME:-}" ]; then
  cat >> /etc/odoo/odoo.conf <<EOF
db_name = ${DB_NAME}
EOF
fi

# Wait for Postgres to be ready (tool from the official Odoo image)
wait-for-psql.py \
  --db_host="${DB_HOST}" \
  --db_port="${DB_PORT}" \
  --db_user="${DB_USER}" \
  --db_password="${DB_PASSWORD}" \
  --timeout=30

# Strip the leading "odoo" arg if the container was started with CMD ["odoo"]
if [ "${1:-}" = "odoo" ]; then shift; fi

exec odoo -c /etc/odoo/odoo.conf "$@"

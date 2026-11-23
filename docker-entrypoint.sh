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
db_maxconn = ${ODOO_DB_MAXCONN:-64}
dbfilter = ${ODOO_DBFILTER:-.*}
list_db = ${ODOO_LIST_DB:-True}
proxy_mode = ${ODOO_PROXY_MODE:-False}
xmlrpc_port = ${ODOO_XMLRPC_PORT:-8069}
longpolling_port = ${ODOO_LONGPOLLING_PORT:-8072}
server_wide_modules = ${ODOO_SERVER_WIDE_MODULES:-base,rpc,web}
log_level = ${ODOO_LOG_LEVEL:-info}
workers = ${ODOO_WORKERS:-0}
max_cron_threads = ${ODOO_MAX_CRON_THREADS:-1}
limit_memory_hard = ${ODOO_LIMIT_MEMORY_HARD:-2684354560}
limit_memory_soft = ${ODOO_LIMIT_MEMORY_SOFT:-2147483648}
limit_time_cpu = ${ODOO_LIMIT_TIME_CPU:-60}
limit_time_real = ${ODOO_LIMIT_TIME_REAL:-120}
limit_time_real_cron = ${ODOO_LIMIT_TIME_REAL_CRON:--1}
websocket_keep_alive_timeout = ${ODOO_WEBSOCKET_KEEP_ALIVE_TIMEOUT:-3600}
websocket_rate_limit_burst = ${ODOO_WEBSOCKET_RATE_LIMIT_BURST:-10}
websocket_rate_limit_delay = ${ODOO_WEBSOCKET_RATE_LIMIT_DELAY:-0.2}
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

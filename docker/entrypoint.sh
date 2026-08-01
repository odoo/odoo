#!/usr/bin/env bash
set -euo pipefail

# Default config path (mounted by compose)
: "${ODOO_RC:=/etc/odoo/odoo.conf}"

: "${ODOO_LONGPOLLING_PORT:=8072}"
: "${ODOO_WORKERS:=0}"
: "${ODOO_MAX_CRON_THREADS:=1}"
: "${ODOO_LIMIT_TIME_CPU:=60}"
: "${ODOO_LIMIT_TIME_REAL:=120}"
: "${ODOO_LIMIT_MEMORY_SOFT:=2147483648}"
: "${ODOO_LIMIT_MEMORY_HARD:=2684354560}"

TEMPLATE_PATH="${ODOO_RC}.template"

if [[ -f "${TEMPLATE_PATH}" ]]; then
  echo "Rendering Odoo config ${ODOO_RC} from template ${TEMPLATE_PATH}..."
  umask 077
  envsubst < "${TEMPLATE_PATH}" > "${ODOO_RC}"
fi

# Ensure data dir exists
mkdir -p /var/lib/odoo

# Wait for Postgres if requested
if [[ -n "${DB_HOST:-}" ]]; then
  echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."
  until pg_isready -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER:-odoo}" >/dev/null 2>&1; do
    sleep 1
  done
fi

echo "Starting Odoo..."
exec "$@"

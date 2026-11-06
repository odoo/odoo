#!/bin/bash
set -e

# Render provides the port in the $PORT environment variable (defaults to 8069 if unset)
HTTP_PORT="${PORT:-8069}"

# Detect application root directory (works in Docker /app or Render Native /opt/render/project/src)
APP_DIR="${APP_DIR:-$(pwd)}"
DATA_DIR="${APP_DIR}/data"
mkdir -p "${DATA_DIR}"

# Normalize uppercase and lowercase environment variables
DB_HOST="${DB_HOST:-${db_host}}"
DB_PORT="${DB_PORT:-${db_port}}"
DB_USER="${DB_USER:-${db_user}}"
DB_PASSWORD="${DB_PASSWORD:-${db_password}}"
DB_NAME="${DB_NAME:-${db_name}}"
DB_SSLMODE="${DB_SSLMODE:-${db_sslmode}}"
ADMIN_PASSWD="${ADMIN_PASSWD:-${admin_passwd}}"
DB_FILTER="${DBFILTER:-${dbfilter}}"
DB_MAXCONN="${DB_MAXCONN:-${db_maxconn}}"
MAX_CRON_THREADS="${MAX_CRON_THREADS:-${max_cron_threads}}"
UPDATE="${UPDATE:-${update}}"
INIT="${INIT:-${init}}"

# If DATABASE_URL is provided, extract any database parameters that have not been set
if [ -n "$DATABASE_URL" ]; then
    eval "$(python3 -c "
import os
from urllib.parse import urlparse
u = urlparse(os.environ.get('DATABASE_URL', ''))
if u.scheme:
    if not os.environ.get('DB_USER') and u.username: print(f'DB_USER=\"{u.username}\"')
    if not os.environ.get('DB_PASSWORD') and u.password: print(f'DB_PASSWORD=\"{u.password}\"')
    if not os.environ.get('DB_HOST') and u.hostname: print(f'DB_HOST=\"{u.hostname}\"')
    if not os.environ.get('DB_PORT') and u.port: print(f'DB_PORT=\"{u.port}\"')
    db = u.path.lstrip('/')
    if not os.environ.get('DB_NAME') and db: print(f'DB_NAME=\"{db}\"')
")"
fi

# Fallback default values
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-postgres}"
DB_SSLMODE="${DB_SSLMODE:-require}"
# Default connection pool bounds to prevent exhausting database poolers
DB_MAXCONN="${DB_MAXCONN:-16}"
MAX_CRON_THREADS="${MAX_CRON_THREADS:-1}"

# Export variables for child python processes
export DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME DB_SSLMODE

# Check if target database has core tables initialized (e.g. ir_act_window)
AUTO_INIT=""
if [ -n "$DB_HOST" ] && [ -n "$DB_USER" ]; then
    AUTO_INIT=$(python3 -c "
import os, sys, psycopg2

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', '5432'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD', ''),
        dbname=os.environ.get('DB_NAME', 'postgres'),
        sslmode=os.environ.get('DB_SSLMODE', 'require'),
        connect_timeout=10,
    )
    with conn.cursor() as cur:
        cur.execute(\"SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='ir_act_window';\")
        has_act_window = bool(cur.fetchone())
    conn.close()

    if not has_act_window:
        print('1')
except Exception as e:
    sys.stderr.write(f'Database inspection warning: {e}\n')
" 2>/dev/null || true)
fi

if [ "$AUTO_INIT" = "1" ]; then
    echo "=========================================================="
    echo " Notice: Core table 'ir_act_window' does not exist in database '${DB_NAME}'."
    echo " Auto-initializing foundational modules: base,school_management,school_website"
    echo "=========================================================="
    INIT="${INIT:-base,school_management,school_website}"
fi

# Build arguments array for Odoo execution
ARGS=(
    "--http-interface=0.0.0.0"
    "--http-port=${HTTP_PORT}"
    "--proxy-mode"
    "--addons-path=${APP_DIR}/addons,${APP_DIR}/odoo/addons,${APP_DIR}/custom"
    "--data-dir=${DATA_DIR}"
)

# Append database configurations if provided
[ -n "$DB_HOST" ] && ARGS+=("--db_host=${DB_HOST}")
[ -n "$DB_PORT" ] && ARGS+=("--db_port=${DB_PORT}")
[ -n "$DB_USER" ] && ARGS+=("--db_user=${DB_USER}")
[ -n "$DB_PASSWORD" ] && ARGS+=("--db_password=${DB_PASSWORD}")
[ -n "$DB_NAME" ] && ARGS+=("--database=${DB_NAME}")
[ -n "$DB_SSLMODE" ] && ARGS+=("--db_sslmode=${DB_SSLMODE}")
[ -n "$ADMIN_PASSWD" ] && ARGS+=("--admin-passwd=${ADMIN_PASSWD}")
[ -n "$DB_FILTER" ] && ARGS+=("--db-filter=${DB_FILTER}")
[ -n "$DB_MAXCONN" ] && ARGS+=("--db_maxconn=${DB_MAXCONN}")
[ -n "$MAX_CRON_THREADS" ] && ARGS+=("--max-cron-threads=${MAX_CRON_THREADS}")

# Module lifecycle flags (e.g., UPDATE=school_management or INIT=school_website)
[ -n "$UPDATE" ] && ARGS+=("-u" "${UPDATE}")
[ -n "$INIT" ] && ARGS+=("-i" "${INIT}")

echo "=========================================================="
echo " Starting Odoo 19 on port: ${HTTP_PORT}"
echo " Database Host: ${DB_HOST:-[not set]}:${DB_PORT}"
echo " Database User: ${DB_USER:-[not set]}"
echo " Database Name: ${DB_NAME}"
echo " Database SSL:  ${DB_SSLMODE}"
echo " Max Conn:      ${DB_MAXCONN}"
echo " Max Cron:      ${MAX_CRON_THREADS}"
[ -n "$UPDATE" ] && echo " Update Module: ${UPDATE}"
[ -n "$INIT" ] && echo " Init Module:   ${INIT}"
echo " Addons path:   ${APP_DIR}/addons,${APP_DIR}/odoo/addons,${APP_DIR}/custom"
echo " Proxy Mode:    Enabled"
echo " Data dir:      ${DATA_DIR}"
echo "=========================================================="

exec python3 "${APP_DIR}/odoo-bin" "${ARGS[@]}" "$@"

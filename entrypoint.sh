#!/bin/bash
set -e

# Render provides the port in the $PORT environment variable (defaults to 8069 if unset)
HTTP_PORT="${PORT:-8069}"

# If DATABASE_URL is provided (e.g., from Render PostgreSQL), parse components
if [ -n "$DATABASE_URL" ]; then
    # postgresql://user:password@host:port/dbname
    PROTO="$(echo "$DATABASE_URL" | sed -e's,^\(.*://\).*,\1,g')"
    URL_WITHOUT_PROTO="${DATABASE_URL/$PROTO/}"
    USER_PASS="$(echo "$URL_WITHOUT_PROTO" | grep "@" | cut -d@ -f1)"
    PASS="$(echo "$USER_PASS" | grep ":" | cut -d: -f2)"
    if [ -n "$PASS" ]; then
        USER="$(echo "$USER_PASS" | cut -d: -f1)"
    else
        USER="$USER_PASS"
    fi
    HOST_PORT_DB="$(echo "$URL_WITHOUT_PROTO" | sed -e "s,$USER_PASS@,,g")"
    HOST_PORT="$(echo "$HOST_PORT_DB" | cut -d/ -f1)"
    HOST="$(echo "$HOST_PORT" | cut -d: -f1)"
    PORT_NUM="$(echo "$HOST_PORT" | grep ":" | cut -d: -f2)"
    DB="$(echo "$HOST_PORT_DB" | cut -d/ -f2 | cut -d? -f1)"

    [ -z "$DB_USER" ] && DB_USER="$USER"
    [ -z "$DB_PASSWORD" ] && DB_PASSWORD="$PASS"
    [ -z "$DB_HOST" ] && DB_HOST="$HOST"
    [ -z "$DB_PORT" ] && DB_PORT="${PORT_NUM:-5432}"
    [ -z "$DB_NAME" ] && DB_NAME="$DB"
fi

# Build arguments array for Odoo execution
ARGS=(
    "--http-interface=0.0.0.0"
    "--http-port=${HTTP_PORT}"
    "--proxy-mode"
    "--addons-path=/app/addons,/app/odoo/addons,/app/custom"
    "--data-dir=/app/data"
)

# Append database configurations if provided
[ -n "$DB_HOST" ] && ARGS+=("--db_host=${DB_HOST}")
[ -n "$DB_PORT" ] && ARGS+=("--db_port=${DB_PORT}")
[ -n "$DB_USER" ] && ARGS+=("--db_user=${DB_USER}")
[ -n "$DB_PASSWORD" ] && ARGS+=("--db_password=${DB_PASSWORD}")
[ -n "$DB_NAME" ] && ARGS+=("--database=${DB_NAME}")
[ -n "$DB_SSLMODE" ] && ARGS+=("--db_sslmode=${DB_SSLMODE}")
[ -n "$ADMIN_PASSWD" ] && ARGS+=("--admin-passwd=${ADMIN_PASSWD}")

echo "=========================================================="
echo " Starting Odoo 19 on port: ${HTTP_PORT}"
echo " Addons path: /app/addons,/app/odoo/addons,/app/custom"
echo " Proxy Mode: Enabled"
echo "=========================================================="

exec python3 odoo-bin "${ARGS[@]}" "$@"

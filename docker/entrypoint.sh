#!/bin/bash
set -euo pipefail

# --- defaults (overridable via environment) ---------------------------------
: "${DB_HOST:=db}"
: "${DB_PORT:=5432}"
: "${DB_USER:=odoo}"
: "${DB_PASSWORD:=}"
: "${ODOO_ADMIN_PASSWD:=}"
: "${ODOO_WORKERS:=5}"
: "${ODOO_LIST_DB:=False}"
: "${ODOO_LOG_LEVEL:=info}"
: "${ODOO_LIMIT_MEMORY_SOFT:=1073741824}"   # 1 GiB per worker
: "${ODOO_LIMIT_MEMORY_HARD:=1342177280}"   # 1.25 GiB per worker

launch_odoo() {
    if [ -z "$DB_PASSWORD" ] || [ -z "$ODOO_ADMIN_PASSWD" ]; then
        echo "Error: DB_PASSWORD and ODOO_ADMIN_PASSWD must be set." >&2
        exit 1
    fi

    # --- wait for postgres --------------------------------------------------
    for i in $(seq 1 30); do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; then
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "Error: PostgreSQL at $DB_HOST:$DB_PORT not ready after 60s, giving up." >&2
            exit 1
        fi
        echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT... ($i/30)"
        sleep 2
    done

    # --- render config from template (only substitute our own variables) ----
    export DB_HOST DB_PORT DB_USER DB_PASSWORD \
        ODOO_ADMIN_PASSWD ODOO_WORKERS ODOO_LIST_DB ODOO_LOG_LEVEL \
        ODOO_LIMIT_MEMORY_SOFT ODOO_LIMIT_MEMORY_HARD
    envsubst '$DB_HOST $DB_PORT $DB_USER $DB_PASSWORD $ODOO_ADMIN_PASSWD $ODOO_WORKERS $ODOO_LIST_DB $ODOO_LOG_LEVEL $ODOO_LIMIT_MEMORY_SOFT $ODOO_LIMIT_MEMORY_HARD' \
        < /etc/odoo/odoo.conf.template > /etc/odoo/odoo.conf

    exec /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf "$@"
}

case "${1:-odoo}" in
    odoo)
        shift || true
        launch_odoo "$@"
        ;;
    -*)
        launch_odoo "$@"
        ;;
    *)
        # arbitrary command (e.g. `docker run ... python`, shell) — run as-is
        exec "$@"
        ;;
esac

#!/usr/bin/env bash
set -euo pipefail

COMPOSE_BIN="${COMPOSE_BIN:-docker compose}"
DB_USER="${DB_USER:-kodoo}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-ktest}"
CREATE_APP_DATABASE="${CREATE_APP_DATABASE:-1}"

require_value() {
    local name="$1"
    local value="$2"
    if [ -z "$value" ]; then
        echo "[dev-project-db-setup] Missing required value: $name"
        exit 1
    fi
}

escape_sql() {
    printf "%s" "$1" | sed "s/'/''/g"
}

should_create_database() {
    case "$CREATE_APP_DATABASE" in
        1|true|TRUE|yes|YES)
            return 0
            ;;
        0|false|FALSE|no|NO)
            return 1
            ;;
        *)
            echo "[dev-project-db-setup] Invalid CREATE_APP_DATABASE value: '$CREATE_APP_DATABASE'"
            exit 1
            ;;
    esac
}

require_value "DB_PASSWORD" "$DB_PASSWORD"

echo "[dev-project-db-setup] starting Docker PostgreSQL..."
$COMPOSE_BIN up -d db

for _ in $(seq 1 30); do
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' kodoo-db 2>/dev/null || true)"
    if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
        break
    fi
    sleep 2
done

health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' kodoo-db 2>/dev/null || true)"
if [ "$health" != "healthy" ] && [ "$health" != "running" ]; then
    echo "[dev-project-db-setup] Docker PostgreSQL is not ready."
    exit 1
fi

if should_create_database; then
    exists="$($COMPOSE_BIN exec -T -e PGPASSWORD="$DB_PASSWORD" db \
        psql -h 127.0.0.1 -U "$DB_USER" -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname = '$(escape_sql "$DB_NAME")'" | tr -d '[:space:]')"

    if [ "$exists" != "1" ]; then
        echo "[dev-project-db-setup] creating database '$DB_NAME'..."
        $COMPOSE_BIN exec -T -e PGPASSWORD="$DB_PASSWORD" db \
            psql -h 127.0.0.1 -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c \
            "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
    else
        echo "[dev-project-db-setup] database '$DB_NAME' already exists."
    fi
else
    echo "[dev-project-db-setup] Docker PostgreSQL role is ready. Database creation skipped for Odoo database manager mode."
fi

echo "[dev-project-db-setup] Docker PostgreSQL ready on the host binding."

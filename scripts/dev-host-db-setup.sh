#!/usr/bin/env bash
set -euo pipefail

PG_SERVICE="${PG_SERVICE:-postgresql}"
PG_SUPERUSER="${PG_SUPERUSER:-postgres}"
APP_DB_USER="${APP_DB_USER:-kodoo}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-}"
APP_DB_NAME="${APP_DB_NAME:-kodoo}"
TEST_DB_NAME="${TEST_DB_NAME:-ktest}"

require_value() {
    local name="$1"
    local value="$2"
    if [ -z "$value" ]; then
        echo "[dev-host-db-setup] Missing required value: $name"
        exit 1
    fi
    case "$value" in
        *$'\n'*|*$'\r'*)
            echo "[dev-host-db-setup] $name cannot contain newlines."
            exit 1
            ;;
    esac
}

escape_sql() {
    printf "%s" "$1" | sed "s/'/''/g"
}

role_exists() {
    sudo -u "$PG_SUPERUSER" psql -d postgres -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname = '$(escape_sql "$APP_DB_USER")'" | grep -q 1
}

db_exists() {
    local db_name="$1"
    sudo -u "$PG_SUPERUSER" psql -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname = '$(escape_sql "$db_name")'" | grep -q 1
}

require_value "APP_DB_PASSWORD" "$APP_DB_PASSWORD"

if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl is-active --quiet "$PG_SERVICE"; then
        echo "[dev-host-db-setup] starting PostgreSQL service '$PG_SERVICE'..."
        sudo systemctl start "$PG_SERVICE"
    fi
else
    echo "[dev-host-db-setup] systemctl not found. Ensure PostgreSQL is already running."
fi

if ! role_exists; then
    echo "[dev-host-db-setup] creating role '$APP_DB_USER'..."
    sudo -u "$PG_SUPERUSER" psql -d postgres -v ON_ERROR_STOP=1 -c \
        "CREATE ROLE \"$APP_DB_USER\" WITH LOGIN PASSWORD '$(escape_sql "$APP_DB_PASSWORD")' CREATEDB;"
else
    echo "[dev-host-db-setup] role '$APP_DB_USER' already exists."
    sudo -u "$PG_SUPERUSER" psql -d postgres -v ON_ERROR_STOP=1 -c \
        "ALTER ROLE \"$APP_DB_USER\" WITH LOGIN PASSWORD '$(escape_sql "$APP_DB_PASSWORD")' CREATEDB;"
fi

for db_name in "$APP_DB_NAME" "$TEST_DB_NAME"; do
    if ! db_exists "$db_name"; then
        echo "[dev-host-db-setup] creating database '$db_name'..."
        sudo -u "$PG_SUPERUSER" createdb --owner="$APP_DB_USER" "$db_name"
    else
        echo "[dev-host-db-setup] database '$db_name' already exists."
    fi
done

echo "[dev-host-db-setup] local PostgreSQL is ready: '$APP_DB_NAME' and '$TEST_DB_NAME'."

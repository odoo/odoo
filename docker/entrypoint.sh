#!/usr/bin/env bash
set -e

DB_HOST="${HOST:-db}"
DB_PORT="${PORT:-5432}"
DB_USER="${USER:-odoo}"

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    sleep 2
done

exec "$@"

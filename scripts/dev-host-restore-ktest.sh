#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/postgres}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
APP_DB_USER="${APP_DB_USER:-kodoo}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-}"
TEST_DB_NAME="${TEST_DB_NAME:-ktest}"
BACKUP_FILE="${1:-${BACKUP_FILE:-$BACKUP_DIR/kodoo_latest.dump}}"

if [ -z "$APP_DB_PASSWORD" ]; then
    echo "[dev-host-restore-ktest] Missing required value: APP_DB_PASSWORD"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[dev-host-restore-ktest] backup file not found: '$BACKUP_FILE'."
    exit 1
fi

echo "[dev-host-restore-ktest] restoring '$BACKUP_FILE' into '$TEST_DB_NAME'..."

PGPASSWORD="$APP_DB_PASSWORD" dropdb \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$APP_DB_USER" \
    --if-exists \
    "$TEST_DB_NAME"

PGPASSWORD="$APP_DB_PASSWORD" createdb \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$APP_DB_USER" \
    -O "$APP_DB_USER" \
    "$TEST_DB_NAME"

PGPASSWORD="$APP_DB_PASSWORD" pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$APP_DB_USER" \
    --no-owner \
    --role="$APP_DB_USER" \
    -d "$TEST_DB_NAME" \
    "$BACKUP_FILE"

echo "[dev-host-restore-ktest] restore complete."

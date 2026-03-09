#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/postgres}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
APP_DB_USER="${APP_DB_USER:-kodoo}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-}"
APP_DB_NAME="${APP_DB_NAME:-kodoo}"

if [ -z "$APP_DB_PASSWORD" ]; then
    echo "[dev-host-backup] Missing required value: APP_DB_PASSWORD"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="$BACKUP_DIR/${APP_DB_NAME}_${timestamp}.dump"
latest_file="$BACKUP_DIR/${APP_DB_NAME}_latest.dump"

echo "[dev-host-backup] creating backup '$backup_file'..."
PGPASSWORD="$APP_DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$APP_DB_USER" \
    -Fc \
    -f "$backup_file" \
    "$APP_DB_NAME"

cp -f "$backup_file" "$latest_file"
echo "[dev-host-backup] latest backup updated at '$latest_file'."

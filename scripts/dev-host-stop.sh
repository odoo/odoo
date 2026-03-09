#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODOO_DEV_PID_FILE="${ODOO_DEV_PID_FILE:-logs/odoo-dev-host.pid}"

if [ ! -f "$ODOO_DEV_PID_FILE" ]; then
    echo "[dev-host-stop] No PID file found. Nothing to stop."
    exit 0
fi

odoo_pid="$(cat "$ODOO_DEV_PID_FILE" 2>/dev/null || true)"
if [ -z "$odoo_pid" ]; then
    rm -f "$ODOO_DEV_PID_FILE"
    echo "[dev-host-stop] Empty PID file removed."
    exit 0
fi

if kill -0 "$odoo_pid" 2>/dev/null; then
    echo "[dev-host-stop] stopping Odoo PID $odoo_pid..."
    kill "$odoo_pid"
    sleep 2
    if kill -0 "$odoo_pid" 2>/dev/null; then
        kill -9 "$odoo_pid"
    fi
else
    echo "[dev-host-stop] PID $odoo_pid is not running."
fi

rm -f "$ODOO_DEV_PID_FILE"
echo "[dev-host-stop] done."

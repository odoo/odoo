#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-venv/bin/python3}"
ODOO_BIN_PATH="${ODOO_BIN_PATH:-./odoo-bin}"
ODOO_DEV_CONFIG="${ODOO_DEV_CONFIG:-deploy/odoo/kodoo.dev-host.local.conf}"
ODOO_DEV_DB="${ODOO_DEV_DB:-kodoo}"
ODOO_DEV_LOG_PATH="${ODOO_DEV_LOG_PATH:-logs/odoo-dev-host.log}"
ODOO_DEV_PID_FILE="${ODOO_DEV_PID_FILE:-logs/odoo-dev-host.pid}"
ODOO_DEV_HTTP_PORT="${ODOO_DEV_HTTP_PORT:-8070}"

mkdir -p "$(dirname "$ODOO_DEV_LOG_PATH")"

if [ -f "$ODOO_DEV_PID_FILE" ]; then
    existing_pid="$(cat "$ODOO_DEV_PID_FILE" 2>/dev/null || true)"
    if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "[dev-host-start] Odoo already running with PID $existing_pid."
        exit 0
    fi
    rm -f "$ODOO_DEV_PID_FILE"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "[dev-host-start] Python executable not found at '$PYTHON_BIN'."
    exit 1
fi

echo "[dev-host-start] starting Odoo locally on database '$ODOO_DEV_DB'..."
nohup "$PYTHON_BIN" "$ODOO_BIN_PATH" \
    -c "$ODOO_DEV_CONFIG" \
    -d "$ODOO_DEV_DB" \
    --logfile="$ODOO_DEV_LOG_PATH" \
    --log-level=info \
    >/dev/null 2>&1 &

odoo_pid="$!"
echo "$odoo_pid" > "$ODOO_DEV_PID_FILE"
sleep 3

if ! kill -0 "$odoo_pid" 2>/dev/null; then
    echo "[dev-host-start] Odoo process exited during startup. Recent log:"
    tail -n 40 "$ODOO_DEV_LOG_PATH" 2>/dev/null || true
    rm -f "$ODOO_DEV_PID_FILE"
    exit 1
fi

echo "[dev-host-start] Odoo running with PID $odoo_pid."
echo "[dev-host-start] Local URL: http://127.0.0.1:$ODOO_DEV_HTTP_PORT"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="$ROOT_DIR/services/forge_engine"

FORGE_ENGINE_PYTHON_BIN="${FORGE_ENGINE_PYTHON_BIN:-$ENGINE_DIR/.venv/bin/python}"
FORGE_ENGINE_HOST="${FORGE_ENGINE_HOST:-127.0.0.1}"
FORGE_ENGINE_PORT="${FORGE_ENGINE_PORT:-8765}"
FORGE_ENGINE_LOG_PATH="${FORGE_ENGINE_LOG_PATH:-$ROOT_DIR/logs/forge-engine.log}"
FORGE_ENGINE_PID_FILE="${FORGE_ENGINE_PID_FILE:-$ROOT_DIR/logs/forge-engine.pid}"

FORGE_DB_HOST="${FORGE_DB_HOST:-127.0.0.1}"
FORGE_DB_PORT="${FORGE_DB_PORT:-5432}"
FORGE_DB_USER="${FORGE_DB_USER:-kodoo}"
FORGE_DB_PASSWORD="${FORGE_DB_PASSWORD:-}"
FORGE_DB_NAME="${FORGE_DB_NAME:-kodoo_studio}"

ADDONS_PATH="${ADDONS_PATH:-$ROOT_DIR/addons}"
OUTPUT_PATH="${OUTPUT_PATH:-/tmp/forge_output}"
TERMINAL_SECRET="${TERMINAL_SECRET:-}"
ODOO_RUNTIME_MODE="${ODOO_RUNTIME_MODE:-direct}"
ODOO_URL="${ODOO_URL:-http://127.0.0.1:8069}"
ODOO_DB="${ODOO_DB:-$FORGE_DB_NAME}"
ODOO_USER="${ODOO_USER:-$FORGE_DB_USER}"
ODOO_PASSWORD="${ODOO_PASSWORD:-$FORGE_DB_PASSWORD}"

urlencode() {
    python3 - "$1" <<'PY'
import sys
from urllib.parse import quote

print(quote(sys.argv[1], safe=""))
PY
}

if [ -f "$FORGE_ENGINE_PID_FILE" ]; then
    existing_pid="$(cat "$FORGE_ENGINE_PID_FILE" 2>/dev/null || true)"
    if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "[forge-engine-start] forge_engine already running with PID $existing_pid."
        exit 0
    fi
    rm -f "$FORGE_ENGINE_PID_FILE"
fi

if [ ! -x "$FORGE_ENGINE_PYTHON_BIN" ]; then
    echo "[forge-engine-start] Python executable not found at '$FORGE_ENGINE_PYTHON_BIN'."
    exit 1
fi

if [ -z "$TERMINAL_SECRET" ]; then
    echo "[forge-engine-start] TERMINAL_SECRET is required."
    exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
    encoded_user="$(urlencode "$FORGE_DB_USER")"
    encoded_password="$(urlencode "$FORGE_DB_PASSWORD")"
    export DATABASE_URL="postgresql+asyncpg://${encoded_user}:${encoded_password}@${FORGE_DB_HOST}:${FORGE_DB_PORT}/${FORGE_DB_NAME}"
fi

export ADDONS_PATH OUTPUT_PATH TERMINAL_SECRET ODOO_RUNTIME_MODE ODOO_URL ODOO_DB ODOO_USER ODOO_PASSWORD

mkdir -p "$(dirname "$FORGE_ENGINE_LOG_PATH")" "$OUTPUT_PATH"

cd "$ENGINE_DIR"
nohup "$FORGE_ENGINE_PYTHON_BIN" -m uvicorn main:app --host "$FORGE_ENGINE_HOST" --port "$FORGE_ENGINE_PORT" >>"$FORGE_ENGINE_LOG_PATH" 2>&1 &

engine_pid="$!"
echo "$engine_pid" > "$FORGE_ENGINE_PID_FILE"
sleep 2

if ! kill -0 "$engine_pid" 2>/dev/null; then
    echo "[forge-engine-start] forge_engine exited during startup. Recent log:"
    tail -n 60 "$FORGE_ENGINE_LOG_PATH" 2>/dev/null || true
    rm -f "$FORGE_ENGINE_PID_FILE"
    exit 1
fi

echo "[forge-engine-start] forge_engine running with PID $engine_pid."
echo "[forge-engine-start] Health URL: http://$FORGE_ENGINE_HOST:$FORGE_ENGINE_PORT/health"
echo "[forge-engine-start] Output path: $OUTPUT_PATH"

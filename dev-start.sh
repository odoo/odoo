#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$REPO_DIR/.odoo-dev.pid"
LOG_FILE="/tmp/odoo-dev.log"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Odoo already running (PID $(cat "$PID_FILE"))"
    exit 0
fi

export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"

"$REPO_DIR/.venv/bin/python" "$REPO_DIR/odoo-bin" \
    -d odoo-dev \
    --addons-path=addons,odoo/addons \
    --dev=all \
    >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Odoo started (PID $!, log: $LOG_FILE)"
echo "Open: http://localhost:8069"

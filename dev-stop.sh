#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$REPO_DIR/.odoo-dev.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file found — server not running?"
    exit 0
fi

PID="$(cat "$PID_FILE")"

if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Odoo stopped (PID $PID)"
else
    echo "Process $PID not found — already stopped"
fi

rm -f "$PID_FILE"

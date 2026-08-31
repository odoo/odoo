#!/usr/bin/env bash

set -euo pipefail

ROOT="/Users/adrianpichardo/Documents/Odoo/odoo"
PG_CTL="/opt/homebrew/opt/postgresql@16/bin/pg_ctl"
PG_DATA="$ROOT/.postgres"
PG_SOCKET="$ROOT/.postgres_socket"
PG_LOG="$ROOT/postgres.log"
ODOO_BIN="$ROOT/odoo-bin"
ODOO_LOG="$ROOT/odoo.log"
ODOO_CONF="$ROOT/odoo.conf"
PYTHON_BIN="$ROOT/.venv/bin/python"
SCREEN_NAME="odoo_local"
ODOO_MATCH="$ODOO_BIN -c $ODOO_CONF -d odoo_dev"

mkdir -p "$PG_SOCKET"

if ! "$PG_CTL" -D "$PG_DATA" status >/dev/null 2>&1; then
  "$PG_CTL" -D "$PG_DATA" -l "$PG_LOG" -o "-p 5433 -k $PG_SOCKET" start
fi

if pgrep -f "$ODOO_MATCH" >/dev/null 2>&1; then
  echo "Odoo is already running"
  exit 0
fi

screen -dmS "$SCREEN_NAME" bash -lc "cd '$ROOT' && exec '$PYTHON_BIN' '$ODOO_BIN' -c '$ODOO_CONF' -d odoo_dev >>'$ODOO_LOG' 2>&1"
sleep 2
if ! pgrep -f "$ODOO_MATCH" >/dev/null 2>&1; then
  echo "Odoo failed to stay up; check $ODOO_LOG" >&2
  exit 1
fi
echo "Odoo started"

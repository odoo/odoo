#!/usr/bin/env bash

set -euo pipefail

ROOT="/Users/adrianpichardo/Documents/Odoo/odoo"
PG_CTL="/opt/homebrew/opt/postgresql@16/bin/pg_ctl"
PG_DATA="$ROOT/.postgres"
ODOO_BIN="$ROOT/odoo-bin"
ODOO_CONF="$ROOT/odoo.conf"
ODOO_MATCH="$ODOO_BIN -c $ODOO_CONF -d odoo_dev"

if pgrep -f "$ODOO_MATCH" >/dev/null 2>&1; then
  pkill -f "$ODOO_MATCH"
  echo "Stopped Odoo"
fi

if "$PG_CTL" -D "$PG_DATA" status >/dev/null 2>&1; then
  "$PG_CTL" -D "$PG_DATA" stop
fi

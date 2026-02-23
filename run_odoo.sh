#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .venv/bin/activate ]]; then
  echo "No existe .venv en $ROOT_DIR"
  exit 1
fi

source .venv/bin/activate

DB_NAME="${1:-mydb_v18}"
if [[ $# -gt 0 ]]; then
  shift
fi

exec ./odoo-bin -c debian/odoo.conf -d "$DB_NAME" "$@"

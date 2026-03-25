#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_OUTPUT="${CONFIG_OUTPUT:-$ROOT_DIR/deploy/odoo/kodoo.prod.local.conf}"
PROD_ADMIN_PASSWORD="${PROD_ADMIN_PASSWORD:-}"
PROD_DB_HOST="${PROD_DB_HOST:-db}"
PROD_DB_PORT="${PROD_DB_PORT:-5432}"
PROD_DB_USER="${PROD_DB_USER:-kodoo}"
PROD_DB_PASSWORD="${PROD_DB_PASSWORD:-}"
PROD_LIST_DB="${PROD_LIST_DB:-True}"
PROD_DBFILTER="${PROD_DBFILTER:-^%d$}"

require_value() {
    local name="$1"
    local value="$2"
    if [ -z "$value" ]; then
        echo "[render-prod-config] Missing required value: $name"
        exit 1
    fi
    case "$value" in
        *$'\n'*|*$'\r'*)
            echo "[render-prod-config] $name cannot contain newlines."
            exit 1
            ;;
    esac
}

require_value "PROD_ADMIN_PASSWORD" "$PROD_ADMIN_PASSWORD"
require_value "PROD_DB_PASSWORD" "$PROD_DB_PASSWORD"

mkdir -p "$(dirname "$CONFIG_OUTPUT")"

EXTRA_ADDONS_PATHS="$(scripts/build-custom-addon-paths.sh /mnt/custom-addons)"
ADDONS_PATH="/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons,/mnt/custom-addons"
if [ -n "$EXTRA_ADDONS_PATHS" ]; then
    ADDONS_PATH="$ADDONS_PATH,$EXTRA_ADDONS_PATHS"
fi

cat > "$CONFIG_OUTPUT" <<EOF
[options]
; Generated locally by scripts/render-prod-config.sh. Do not commit.
admin_passwd = $PROD_ADMIN_PASSWORD

db_host = $PROD_DB_HOST
db_port = $PROD_DB_PORT
db_user = $PROD_DB_USER
db_password = $PROD_DB_PASSWORD

addons_path = $ADDONS_PATH

proxy_mode = True
list_db = $PROD_LIST_DB
dbfilter = $PROD_DBFILTER

http_port = 8069
http_interface = 0.0.0.0
gevent_port = 8072

workers = 2
max_cron_threads = 1
limit_time_cpu = 600
limit_time_real = 1200
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648

log_level = info
EOF

chmod 644 "$CONFIG_OUTPUT"
echo "[render-prod-config] wrote $CONFIG_OUTPUT"

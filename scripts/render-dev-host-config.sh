#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_OUTPUT="${CONFIG_OUTPUT:-$ROOT_DIR/deploy/odoo/kodoo.dev-host.local.conf}"
DEV_HOST_ADMIN_PASSWORD="${DEV_HOST_ADMIN_PASSWORD:-}"
APP_DB_HOST="${APP_DB_HOST:-127.0.0.1}"
APP_DB_PORT="${APP_DB_PORT:-5432}"
APP_DB_USER="${APP_DB_USER:-kodoo}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-}"
APP_HTTP_PORT="${APP_HTTP_PORT:-8070}"

require_value() {
    local name="$1"
    local value="$2"
    if [ -z "$value" ]; then
        echo "[render-dev-host-config] Missing required value: $name"
        exit 1
    fi
    case "$value" in
        *$'\n'*|*$'\r'*)
            echo "[render-dev-host-config] $name cannot contain newlines."
            exit 1
            ;;
    esac
}

require_value "DEV_HOST_ADMIN_PASSWORD" "$DEV_HOST_ADMIN_PASSWORD"
require_value "APP_DB_PASSWORD" "$APP_DB_PASSWORD"

mkdir -p "$(dirname "$CONFIG_OUTPUT")"

EXTRA_ADDONS_PATHS="$(scripts/build-custom-addon-paths.sh custom_addons)"
ADDONS_PATH="addons,custom_addons"
if [ -n "$EXTRA_ADDONS_PATHS" ]; then
    ADDONS_PATH="$ADDONS_PATH,$EXTRA_ADDONS_PATHS"
fi

cat > "$CONFIG_OUTPUT" <<EOF
[options]
; Generated locally by scripts/render-dev-host-config.sh. Do not commit.
admin_passwd = $DEV_HOST_ADMIN_PASSWORD

db_host = $APP_DB_HOST
db_port = $APP_DB_PORT
db_user = $APP_DB_USER
db_password = $APP_DB_PASSWORD

addons_path = $ADDONS_PATH

proxy_mode = False
list_db = True

http_port = $APP_HTTP_PORT
http_interface = 127.0.0.1

workers = 0
max_cron_threads = 1

log_level = info
EOF

chmod 600 "$CONFIG_OUTPUT"
echo "[render-dev-host-config] wrote $CONFIG_OUTPUT"

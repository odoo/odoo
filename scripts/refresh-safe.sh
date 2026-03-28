#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MAKE_BIN="${MAKE:-make}"
DRY_RUN="${REFRESH_SAFE_DRY_RUN:-0}"
ODOO_CONTAINER="${ODOO_CONTAINER:-kodoo-odoo}"
NGINX_CONTAINER="${NGINX_CONTAINER:-kodoo-nginx}"
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-kodoo-ollama}"
CLOUDFLARED_CONTAINER="${CLOUDFLARED_CONTAINER:-kodoo-cloudflared}"

PROD_CONFIG_PATH="${PROD_CONFIG:-deploy/odoo/kodoo.prod.local.conf}"
DEV_HOST_CONFIG_PATH="${DEV_HOST_CONFIG:-deploy/odoo/kodoo.dev-host.local.conf}"
DEV_PROJECT_CONFIG_PATH="${DEV_PROJECT_CONFIG:-deploy/odoo/kodoo.dev-project.local.conf}"

DEV_HOST_PID_PATH="${DEV_HOST_PID_FILE:-logs/odoo-dev-host.pid}"
DEV_HOST_LOG_PATH_VALUE="${DEV_HOST_LOG_PATH:-logs/odoo-dev-host.log}"
DEV_HOST_DB_NAME="${DEV_HOST_DB:-kodoo}"
DEV_HOST_HTTP_PORT_VALUE="${DEV_HOST_HTTP_PORT:-8070}"

DEV_PROJECT_PID_PATH="${DEV_PROJECT_PID_FILE:-logs/odoo-dev-project.pid}"
DEV_PROJECT_LOG_PATH_VALUE="${DEV_PROJECT_LOG_PATH:-logs/odoo-dev-project.log}"
DEV_PROJECT_DB_NAME="${DEV_PROJECT_DB:-ktest}"
DEV_PROJECT_HTTP_PORT_VALUE="${DEV_PROJECT_HTTP_PORT:-8071}"

PYTHON_BIN_VALUE="${PYTHON:-python3}"

log() {
    echo "[refresh-safe] $*"
}

run_cmd() {
    log "+ $*"
    if [ "$DRY_RUN" = "1" ]; then
        return 0
    fi
    "$@"
}

run_make_required() {
    local target="$1"
    run_cmd "$MAKE_BIN" --no-print-directory "$target"
}

run_make_optional() {
    local target="$1"
    log "+ $MAKE_BIN --no-print-directory $target"
    if [ "$DRY_RUN" = "1" ]; then
        return 0
    fi
    if ! "$MAKE_BIN" --no-print-directory "$target"; then
        log "WARN: optional target failed and was skipped: make $target"
    fi
}

pid_running() {
    local pid_file="$1"
    if [ ! -f "$pid_file" ]; then
        return 1
    fi
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -z "$pid" ]; then
        return 1
    fi
    kill -0 "$pid" 2>/dev/null
}

container_running() {
    local container_name="$1"
    [ -n "$(docker ps --filter "name=^/${container_name}$" --filter status=running --quiet 2>/dev/null)" ]
}

container_exists() {
    local container_name="$1"
    docker inspect "$container_name" >/dev/null 2>&1
}

get_compose_config_files() {
    local container_name="$1"
    docker inspect \
        --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' \
        "$container_name" 2>/dev/null || true
}

populate_active_compose_args() {
    local config_files
    config_files="$(get_compose_config_files "$ODOO_CONTAINER")"
    if [ -z "$config_files" ]; then
        return 1
    fi

    ACTIVE_COMPOSE_ARGS=()
    IFS=',' read -r -a compose_files <<<"$config_files"
    for compose_file in "${compose_files[@]}"; do
        [ -n "$compose_file" ] || continue
        ACTIVE_COMPOSE_ARGS+=(-f "$compose_file")
    done

    [ "${#ACTIVE_COMPOSE_ARGS[@]}" -gt 0 ]
}

populate_refresh_services() {
    local compose_services=()
    local service

    mapfile -t compose_services < <(docker compose "${ACTIVE_COMPOSE_ARGS[@]}" config --services)
    ACTIVE_REFRESH_SERVICES=()
    for service in "${compose_services[@]}"; do
        case "$service" in
            odoo|nginx|ollama|cloudflared)
                ACTIVE_REFRESH_SERVICES+=("$service")
                ;;
        esac
    done

    if [ "${#ACTIVE_REFRESH_SERVICES[@]}" -eq 0 ]; then
        ACTIVE_REFRESH_SERVICES=(odoo)
    fi
}

refresh_host_dev() {
    log "Detected active mode: dev-host"
    run_make_required "dev-host-config"
    if [ -f "$PROD_CONFIG_PATH" ]; then
        run_make_optional "prod-config"
    fi
    if [ -f "$DEV_PROJECT_CONFIG_PATH" ]; then
        run_make_optional "dev-project-config"
    fi
    run_cmd env \
        ODOO_DEV_PID_FILE="$DEV_HOST_PID_PATH" \
        ./scripts/dev-host-stop.sh
    run_cmd env \
        PYTHON_BIN="$PYTHON_BIN_VALUE" \
        ODOO_DEV_CONFIG="$DEV_HOST_CONFIG_PATH" \
        ODOO_DEV_DB="$DEV_HOST_DB_NAME" \
        ODOO_DEV_LOG_PATH="$DEV_HOST_LOG_PATH_VALUE" \
        ODOO_DEV_PID_FILE="$DEV_HOST_PID_PATH" \
        ODOO_DEV_HTTP_PORT="$DEV_HOST_HTTP_PORT_VALUE" \
        ./scripts/dev-host-start.sh
}

refresh_project_dev() {
    log "Detected active mode: project"
    run_make_required "dev-project-config"
    if [ -f "$PROD_CONFIG_PATH" ]; then
        run_make_optional "prod-config"
    fi
    if [ -f "$DEV_HOST_CONFIG_PATH" ]; then
        run_make_optional "dev-host-config"
    fi
    run_cmd env \
        ODOO_DEV_PID_FILE="$DEV_PROJECT_PID_PATH" \
        ./scripts/dev-host-stop.sh
    run_cmd env \
        PYTHON_BIN="$PYTHON_BIN_VALUE" \
        ODOO_DEV_CONFIG="$DEV_PROJECT_CONFIG_PATH" \
        ODOO_DEV_DB="$DEV_PROJECT_DB_NAME" \
        ODOO_DEV_LOG_PATH="$DEV_PROJECT_LOG_PATH_VALUE" \
        ODOO_DEV_PID_FILE="$DEV_PROJECT_PID_PATH" \
        ODOO_DEV_HTTP_PORT="$DEV_PROJECT_HTTP_PORT_VALUE" \
        ./scripts/dev-host-start.sh
}

refresh_container_runtime() {
    log "Detected active mode: docker"
    run_make_required "prod-config"
    if [ -f "$DEV_HOST_CONFIG_PATH" ]; then
        run_make_optional "dev-host-config"
    fi
    if [ -f "$DEV_PROJECT_CONFIG_PATH" ]; then
        run_make_optional "dev-project-config"
    fi
    if ! populate_active_compose_args; then
        log "WARN: active compose labels not found on $ODOO_CONTAINER; falling back to docker restart."
        run_cmd docker restart "$ODOO_CONTAINER"
        return
    fi
    populate_refresh_services
    run_cmd docker compose "${ACTIVE_COMPOSE_ARGS[@]}" build odoo
    run_cmd docker compose "${ACTIVE_COMPOSE_ARGS[@]}" up -d --force-recreate "${ACTIVE_REFRESH_SERVICES[@]}"
}

refresh_configs_only() {
    log "No active Odoo runtime detected. Refreshing configs only."
    run_make_required "prod-config"
    if [ -f "$DEV_HOST_CONFIG_PATH" ]; then
        run_make_optional "dev-host-config"
    fi
    if [ -f "$DEV_PROJECT_CONFIG_PATH" ]; then
        run_make_optional "dev-project-config"
    fi
}

main() {
    if pid_running "$DEV_PROJECT_PID_PATH"; then
        refresh_project_dev
    elif pid_running "$DEV_HOST_PID_PATH"; then
        refresh_host_dev
    elif container_running "$ODOO_CONTAINER"; then
        refresh_container_runtime
    elif container_exists "$ODOO_CONTAINER"; then
        log "Odoo container exists but is not running."
        refresh_configs_only
    else
        refresh_configs_only
    fi
    log "Refresh complete."
}

main "$@"

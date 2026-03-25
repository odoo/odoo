#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

load_env_file() {
    local path="$1"
    local raw line key value
    while IFS= read -r raw || [ -n "$raw" ]; do
        line="${raw#"${raw%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [ -n "$line" ] || continue
        [[ "${line:0:1}" == "#" ]] && continue
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*(\?=|:=|=)[[:space:]]*(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[3]}"
            value="${value#"${value%%[![:space:]]*}"}"
            value="${value%"${value##*[![:space:]]}"}"
            if [ "${#value}" -ge 2 ]; then
                case "$value" in
                    \"*\"|\'*\')
                        if [ "${value:0:1}" = "${value: -1}" ]; then
                            value="${value:1:${#value}-2}"
                        fi
                        ;;
                esac
            fi
            printf -v "$key" '%s' "$value"
            export "$key"
        fi
    done < "$path"
}

if [ -f .env ]; then
    load_env_file ./.env
elif [ -f .env.make ]; then
    load_env_file ./.env.make
fi

DB_USER="${PROD_DB_USER:-${PG_LOCAL_USER:-kodoo}}"
DB_HOST="${PG_LOCAL_HOST:-127.0.0.1}"
DB_PORT="${PG_LOCAL_PORT:-5432}"
DB_PASSWORD="${PG_LOCAL_PASSWORD:-${PROD_DB_PASSWORD:-}}"
PROD_NAME="${PROD_DB_NAME:-kodoo}"
DEV_HOST_NAME="${DEV_HOST_DB:-kodoo}"
DEV_TEST_NAME="${DEV_HOST_TEST_DB:-ktest}"
DEV_PROJECT_NAME="${DEV_PROJECT_DB:-ktest}"
DB_MANAGER_BACKEND="${DB_MANAGER_BACKEND:-auto}"

detect_backend() {
    case "$DB_MANAGER_BACKEND" in
        docker|local)
            echo "$DB_MANAGER_BACKEND"
            return 0
            ;;
        auto) ;;
        *)
            echo "[db-manager] Invalid DB_MANAGER_BACKEND: $DB_MANAGER_BACKEND" >&2
            return 1
            ;;
    esac
    if [ "$(docker inspect -f '{{.State.Running}}' kodoo-db 2>/dev/null || true)" = "true" ]; then
        echo "docker"
        return 0
    fi
    if command -v psql >/dev/null 2>&1; then
        echo "local"
        return 0
    fi
    return 1
}

run_psql() {
    local backend
    backend="$(detect_backend)" || {
        echo "[db-manager] No PostgreSQL backend available." >&2
        exit 1
    }
    if [ "$backend" = "docker" ]; then
        docker exec -i kodoo-db psql -U "$DB_USER" -d postgres "$@"
        return 0
    fi
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres "$@"
}

run_createdb() {
    local backend
    backend="$(detect_backend)" || {
        echo "[db-manager] No PostgreSQL backend available." >&2
        exit 1
    }
    if [ "$backend" = "docker" ]; then
        docker exec -i kodoo-db createdb -U "$DB_USER" "$@"
        return 0
    fi
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$@"
}

run_dropdb() {
    local backend
    backend="$(detect_backend)" || {
        echo "[db-manager] No PostgreSQL backend available." >&2
        exit 1
    }
    if [ "$backend" = "docker" ]; then
        docker exec -i kodoo-db dropdb -U "$DB_USER" "$@"
        return 0
    fi
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$@"
}

database_tags() {
    local name="$1"
    local -a tags=()
    [ "$name" = "$PROD_NAME" ] && tags+=("prod")
    [ "$name" = "$DEV_HOST_NAME" ] && tags+=("dev-host")
    [ "$name" = "$DEV_TEST_NAME" ] && tags+=("ktest")
    [ "$name" = "$DEV_PROJECT_NAME" ] && tags+=("project")
    (IFS=,; echo "${tags[*]:--}")
}

list_databases_raw() {
    run_psql -At -F '|' -c \
        "SELECT datname, pg_get_userbyid(datdba), pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datistemplate = false ORDER BY datname;"
}

list_databases_pretty() {
    local backend raw_output
    backend="$(detect_backend 2>/dev/null || true)"
    if [ -z "$backend" ]; then
        echo "[db-manager] No PostgreSQL backend available."
        return 1
    fi
    raw_output="$(list_databases_raw 2>&1)" || {
        echo "[db-manager] Database query failed: $raw_output"
        return 1
    }
    printf "%-28s %-12s %-16s %-12s %s\n" "Database" "Backend" "Owner" "Size" "Tags"
    printf "%-28s %-12s %-16s %-12s %s\n" "----------------------------" "------------" "----------------" "------------" "----------------"
    while IFS='|' read -r name owner size; do
        [ -n "$name" ] || continue
        printf "%-28s %-12s %-16s %-12s %s\n" "$name" "$backend" "$owner" "$size" "$(database_tags "$name")"
    done <<< "$raw_output"
}

list_databases_machine() {
    local backend raw_output
    backend="$(detect_backend 2>/dev/null || true)"
    if [ -z "$backend" ]; then
        echo "[db-manager] No PostgreSQL backend available." >&2
        return 1
    fi
    raw_output="$(list_databases_raw 2>&1)" || {
        echo "[db-manager] Database query failed: $raw_output" >&2
        return 1
    }
    while IFS='|' read -r name owner size; do
        [ -n "$name" ] || continue
        printf "%s|%s|%s|%s|%s\n" "$name" "$backend" "$owner" "$size" "$(database_tags "$name")"
    done <<< "$raw_output"
}

read_database_name() {
    local prompt="$1"
    local value=""
    while [ -z "$value" ]; do
        printf "%s" "$prompt"
        read -r value
    done
    printf "%s" "$value"
}

choose_database() {
    local raw_output
    raw_output="$(list_databases_raw 2>/dev/null)" || {
        echo "[db-manager] Database query failed." >&2
        return 1
    }
    mapfile -t db_names < <(printf "%s\n" "$raw_output" | cut -d'|' -f1)
    if [ "${#db_names[@]}" -eq 0 ]; then
        echo "[db-manager] No databases found." >&2
        return 1
    fi
    if command -v fzf >/dev/null 2>&1; then
        printf "%s\n" "${db_names[@]}" | fzf --prompt='database > ' --height=60% --layout=reverse --border
        return 0
    fi
    echo "Available databases:"
    select choice in "${db_names[@]}"; do
        if [ -n "${choice:-}" ]; then
            printf "%s" "$choice"
            return 0
        fi
        echo "Invalid choice."
    done
}

create_database() {
    local name="${1:-}"
    if [ -z "$name" ]; then
        name="$(read_database_name 'New database name: ')"
    fi
    run_createdb "$name"
    echo "[db-manager] Created database: $name"
}

clone_database() {
    local source="${1:-}"
    local target="${2:-}"
    if [ -z "$source" ]; then
        source="$(choose_database)"
    fi
    if [ -z "$target" ]; then
        target="$(read_database_name "Clone target for '$source': ")"
    fi
    run_createdb -T "$source" "$target"
    echo "[db-manager] Cloned database '$source' into '$target'"
}

drop_database() {
    local name="${1:-}"
    local confirmation=""
    if [ -z "$name" ]; then
        name="$(choose_database)"
    fi
    case "$name" in
        postgres|template0|template1)
            echo "[db-manager] Refusing to drop protected database: $name" >&2
            exit 1
            ;;
    esac
    printf "Type '%s' to confirm drop: " "$name"
    read -r confirmation
    if [ "$confirmation" != "$name" ]; then
        echo "[db-manager] Confirmation did not match. Aborted."
        exit 1
    fi
    run_dropdb --if-exists "$name"
    echo "[db-manager] Dropped database: $name"
}

interactive_menu() {
    if [ ! -t 0 ] || [ ! -t 1 ]; then
        echo "[db-manager] Interactive mode requires a terminal."
        echo "[db-manager] Use: make db-list"
        exit 1
    fi
    while true; do
        echo
        echo "Kodoo Database Manager"
        echo "1) list databases"
        echo "2) create database"
        echo "3) clone database"
        echo "4) drop database"
        echo "0) exit"
        echo
        printf "Choice: "
        read -r choice
        case "$choice" in
            1) list_databases_pretty ;;
            2) create_database ;;
            3) clone_database ;;
            4) drop_database ;;
            0) exit 0 ;;
            *) echo "Invalid choice." ;;
        esac
    done
}

case "${1:-}" in
    list)
        list_databases_pretty
        ;;
    list-raw)
        list_databases_machine
        ;;
    create)
        create_database "${2:-}"
        ;;
    clone)
        clone_database "${2:-}" "${3:-}"
        ;;
    drop)
        drop_database "${2:-}"
        ;;
    "")
        interactive_menu
        ;;
    *)
        echo "Usage: $0 [list|list-raw|create <name>|clone <source> <target>|drop <name>]" >&2
        exit 1
        ;;
esac

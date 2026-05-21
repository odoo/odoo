#!/usr/bin/env bash
#
# Entrypoint for the Railway-flavoured Odoo image.
#
# Responsibilities:
#   1. Translate Railway-style env vars into Odoo CLI flags / config values.
#      - $DATABASE_URL  : full postgres://user:pass@host:port/db connection string
#      - $PORT          : public HTTP port assigned by Railway
#   2. Honour the discrete PG* / ODOO_* overrides if a user prefers them.
#   3. Wait for Postgres to be reachable before exec'ing Odoo (Railway plugins
#      usually come up before the app, but this avoids race conditions on cold
#      starts).
#   4. exec into odoo-bin so it gets PID 1 and signals propagate cleanly.

set -euo pipefail

log() { printf '[entrypoint] %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# Parse $DATABASE_URL (postgresql://user:password@host:port/database?params)
# into PG* variables that Odoo understands.
# ---------------------------------------------------------------------------
if [[ -n "${DATABASE_URL:-}" ]]; then
    python_parse=$(python3 - <<'PY'
import os
import sys
from urllib.parse import urlparse, unquote

url = urlparse(os.environ["DATABASE_URL"])
if url.scheme not in ("postgres", "postgresql"):
    sys.stderr.write(f"DATABASE_URL scheme must be postgres[ql], got {url.scheme!r}\n")
    sys.exit(1)

def export(name, value):
    if value is None or value == "":
        return
    # single-quote the value for safe `eval` in bash
    escaped = str(value).replace("'", "'\\''")
    print(f"export {name}='{escaped}'")

export("PGHOST", url.hostname)
export("PGPORT", url.port or 5432)
export("PGUSER", unquote(url.username) if url.username else None)
export("PGPASSWORD", unquote(url.password) if url.password else None)
export("PGDATABASE", url.path.lstrip("/") or None)
PY
)
    eval "$python_parse"
fi

: "${PGHOST:=${HOST:-localhost}}"
: "${PGPORT:=5432}"
: "${PGUSER:=odoo}"
: "${PGPASSWORD:=}"
: "${PGDATABASE:=${POSTGRES_DB:-postgres}}"

# Odoo reads these:
export DB_HOST="$PGHOST"
export DB_PORT="$PGPORT"
export DB_USER="$PGUSER"
export DB_PASSWORD="$PGPASSWORD"

# ---------------------------------------------------------------------------
# Wait for Postgres. Bounded so Railway's healthcheck eventually flags us as
# down rather than spinning forever.
# ---------------------------------------------------------------------------
wait_for_postgres() {
    local attempts="${POSTGRES_WAIT_ATTEMPTS:-30}"
    local delay="${POSTGRES_WAIT_DELAY:-2}"
    local i=0
    log "Waiting for Postgres at ${PGHOST}:${PGPORT} (user=${PGUSER}, db=${PGDATABASE})"
    while (( i < attempts )); do
        if PGPASSWORD="$PGPASSWORD" pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; then
            log "Postgres is reachable."
            return 0
        fi
        i=$((i + 1))
        sleep "$delay"
    done
    log "Postgres did not become reachable after $((attempts * delay))s; starting Odoo anyway."
    return 1
}

# ---------------------------------------------------------------------------
# HTTP port. Railway injects $PORT; Odoo's flag is --http-port.
# ---------------------------------------------------------------------------
HTTP_PORT="${PORT:-${ODOO_HTTP_PORT:-8069}}"

# ---------------------------------------------------------------------------
# Build the argv we'll exec. Anything the user passes via CMD/`docker run` is
# appended verbatim so they can override or add modules at boot.
# ---------------------------------------------------------------------------
args=(
    "--config" "${ODOO_RC:-/etc/odoo/odoo.conf}"
    "--http-port" "$HTTP_PORT"
    "--db_host"   "$PGHOST"
    "--db_port"   "$PGPORT"
    "--db_user"   "$PGUSER"
    "--db_password" "$PGPASSWORD"
)

# Bind to all interfaces so Railway's proxy can reach us.
args+=("--http-interface" "0.0.0.0")

# If the operator pinned a single database, pass it through. This is the
# typical Railway setup since each environment gets one Postgres plugin.
if [[ -n "${ODOO_DATABASE:-${PGDATABASE:-}}" && "${PGDATABASE}" != "postgres" ]]; then
    args+=("--database" "${ODOO_DATABASE:-$PGDATABASE}")
fi

# Comma-separated module list to install on first boot, if requested.
if [[ -n "${ODOO_INIT_MODULES:-}" ]]; then
    args+=("--init" "$ODOO_INIT_MODULES" "--stop-after-init")
fi

# Comma-separated module list to update on boot, if requested.
if [[ -n "${ODOO_UPDATE_MODULES:-}" ]]; then
    args+=("--update" "$ODOO_UPDATE_MODULES")
fi

# Extra addons path: /mnt/extra-addons by default (Volume mount point).
if [[ -d "/mnt/extra-addons" ]] && [[ -n "$(ls -A /mnt/extra-addons 2>/dev/null || true)" ]]; then
    args+=("--addons-path" "/opt/odoo/addons,/mnt/extra-addons")
fi

wait_for_postgres || true

case "${1:-odoo}" in
    odoo|odoo-bin)
        shift || true
        log "exec odoo-bin ${args[*]} $*"
        exec /opt/odoo/odoo-bin "${args[@]}" "$@"
        ;;
    shell|scaffold|db|cloc|deploy|populate|server|start|upgrade|tsconfig|gen_translations)
        # Forward Odoo sub-commands verbatim with the same DB plumbing.
        subcmd="$1"; shift
        log "exec odoo-bin $subcmd ${args[*]} $*"
        exec /opt/odoo/odoo-bin "$subcmd" "${args[@]}" "$@"
        ;;
    -*)
        log "exec odoo-bin ${args[*]} $*"
        exec /opt/odoo/odoo-bin "${args[@]}" "$@"
        ;;
    *)
        # Arbitrary command — useful for `docker run ... bash`.
        log "exec $*"
        exec "$@"
        ;;
esac

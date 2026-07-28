#!/usr/bin/env bash
# =============================================================================
# backup.sh — Full Odoo backup (PostgreSQL dump + filestore tar)
#
# Usage:
#   ./scripts/backup.sh                    # backs up all databases
#   ./scripts/backup.sh mydb               # backs up single database
#   ./scripts/backup.sh mydb /custom/path  # custom output directory
#
# Output (in /opt/backups/ or custom path):
#   odoo-db-<dbname>-<timestamp>.dump     # pg_dump -Fc (custom format)
#   odoo-fs-<dbname>-<timestamp>.tar.gz   # filestore tarball
#
# Restore (rehearsed, not theatre):
#   1. Create a throwaway container:
#      docker compose -f docker-compose.yml run --rm db psql -h db -U odoo -c \
#        "CREATE DATABASE restore_test WITH OWNER odoo;"
#   2. Restore the dump:
#      pg_restore -h db -U odoo -d restore_test --no-owner \
#        /opt/backups/odoo-db-<dbname>-<timestamp>.dump
#   3. Restore filestore:
#      tar xzf /opt/backups/odoo-fs-<dbname>-<timestamp>.tar.gz \
#        -C /var/lib/odoo/filestore/
# =============================================================================
set -euo pipefail

# --- Config ----------------------------------------------------------------
COMPOSE_PROJECT="${COMPOSE_PROJECT:-$(basename $(git rev-parse --show-toplevel 2>/dev/null || echo 'odoo'))}"
BACKUP_DIR="${2:-/opt/backups}"
DB_NAME="${1:-}"  # empty = all databases
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ---------------------------------------------------------------------------
# Resolve container names
# ---------------------------------------------------------------------------
DB_CONTAINER=$(docker compose ps -q db 2>/dev/null || echo "")
if [ -z "$DB_CONTAINER" ]; then
    log "ERROR: db container not running. Start the stack first: docker compose up -d"
    exit 1
fi

# ---------------------------------------------------------------------------
# Determine which databases to dump
# ---------------------------------------------------------------------------
if [ -n "$DB_NAME" ]; then
    DATABASES="$DB_NAME"
else
    # List all non-template databases
    DATABASES=$(docker compose exec -T db psql -U odoo -t -A \
        -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';")
fi

BACKUP_COUNT=0

for db in $DATABASES; do
    [ -z "$db" ] && continue
    log "Backing up database: $db"

    # --- PostgreSQL dump (custom format, compressed) -----------------------
    DUMP_FILE="${BACKUP_DIR}/odoo-db-${db}-${TIMESTAMP}.dump"
    docker compose exec -T db pg_dump -U odoo -Fc --no-owner -f "/tmp/${db}.dump" "$db"
    docker compose cp "db:/tmp/${db}.dump" "$DUMP_FILE"
    docker compose exec -T db rm -f "/tmp/${db}.dump"
    log "  Dump: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

    # --- Filestore tarball -------------------------------------------------
    FS_SOURCE="/var/lib/odoo/filestore/${db}"
    FS_FILE="${BACKUP_DIR}/odoo-fs-${db}-${TIMESTAMP}.tar.gz"
    if docker compose exec -T odoo test -d "$FS_SOURCE" 2>/dev/null; then
        docker compose exec -T odoo tar czf "/tmp/fs_${db}.tar.gz" -C /var/lib/odoo "filestore/${db}"
        docker compose cp "odoo:/tmp/fs_${db}.tar.gz" "$FS_FILE"
        docker compose exec -T odoo rm -f "/tmp/fs_${db}.tar.gz"
        log "  Filestore: $FS_FILE ($(du -h "$FS_FILE" | cut -f1))"
    else
        log "  Filestore: not found at $FS_SOURCE, skipping"
    fi

    BACKUP_COUNT=$((BACKUP_COUNT + 1))
done

# --- Prune backups older than RETENTION_DAYS --------------------------------
log "Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "odoo-*.dump" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "odoo-*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete

# --- Summary ----------------------------------------------------------------
log "=== Backup Complete ==="
log "  Databases backed up: ${BACKUP_COUNT}"
log "  Directory: ${BACKUP_DIR}"
log "  Retention: ${RETENTION_DAYS} days"
echo ""
log "RESTORE PROCEDURE (rehearsed):"
echo "  1. Create a throwaway DB:"
echo "     docker compose exec -T db psql -U odoo -c \"CREATE DATABASE restore_test WITH OWNER odoo;\""
echo "  2. Restore the dump:"
echo "     docker compose exec -i db pg_restore -U odoo -d restore_test --no-owner < \\"
echo "       ${BACKUP_DIR}/odoo-db-<dbname>-<timestamp>.dump"
echo "  3. Restore the filestore:"
echo "     docker compose exec -T odoo tar xzf - -C /var/lib/odoo < \\"
echo "       ${BACKUP_DIR}/odoo-fs-<dbname>-<timestamp>.tar.gz"
echo "  4. Verify: Access Odoo at http://localhost:8069 with database 'restore_test'"

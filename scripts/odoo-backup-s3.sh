#!/usr/bin/env bash
# =============================================================================
# odoo-backup-s3.sh — Backup Odoo database + filestore to S3
#
# Called by the odoo-backup.service systemd unit nightly.
# Uses the EC2 instance profile for S3 access (no access keys).
#
# Environment variables (from /etc/odoo-backup.env):
#   S3_BACKUP_BUCKET — S3 bucket name for backups
#   RETENTION_DAYS   — Local retention before deletion (default: 30)
#
# Output structure in S3:
#   s3://<bucket>/daily/<YYYYMMDD>/<dbname>.dump
#   s3://<bucket>/daily/<YYYYMMDD>/<dbname>-filestore.tar.gz
#
# Restore:
#   aws s3 cp s3://<bucket>/daily/20260101/invoice_agent.dump /tmp/
#   pg_restore -d invoice_agent --no-owner /tmp/invoice_agent.dump
# =============================================================================
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- Config ----------------------------------------------------------------
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d)
BACKUP_DIR="/opt/backups/${TIMESTAMP}"

if [ -z "$S3_BACKUP_BUCKET" ]; then
    log "ERROR: S3_BACKUP_BUCKET not set"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# --- Determine databases ---------------------------------------------------
# List all non-template databases
DATABASES=$(docker compose -f /opt/odoo/docker-compose.yml \
    exec -T db psql -U odoo -t -A \
    -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';" 2>/dev/null || echo "")

if [ -z "$DATABASES" ]; then
    log "WARNING: No databases found (is the stack running?)"
    exit 1
fi

BACKUP_COUNT=0

for db in $DATABASES; do
    [ -z "$db" ] && continue
    log "Backing up database: $db"

    # --- PostgreSQL dump (custom format, compressed) -----------------------
    DUMP_FILE="${BACKUP_DIR}/${db}.dump"
    docker compose -f /opt/odoo/docker-compose.yml \
        exec -T db pg_dump -U odoo -Fc --no-owner -f "/tmp/${db}.dump" "$db"
    docker compose -f /opt/odoo/docker-compose.yml \
        cp "db:/tmp/${db}.dump" "$DUMP_FILE"
    docker compose -f /opt/odoo/docker-compose.yml \
        exec -T db rm -f "/tmp/${db}.dump"
    log "  Dump: $(du -h "$DUMP_FILE" | cut -f1)"

    # --- Filestore tarball -------------------------------------------------
    FS_SOURCE="/var/lib/odoo/filestore/${db}"
    FS_FILE="${BACKUP_DIR}/${db}-filestore.tar.gz"
    if docker compose -f /opt/odoo/docker-compose.yml \
        exec -T odoo test -d "$FS_SOURCE" 2>/dev/null; then
        docker compose -f /opt/odoo/docker-compose.yml \
            exec -T odoo tar czf "/tmp/fs_${db}.tar.gz" -C /var/lib/odoo "filestore/${db}"
        docker compose -f /opt/odoo/docker-compose.yml \
            cp "odoo:/tmp/fs_${db}.tar.gz" "$FS_FILE"
        docker compose -f /opt/odoo/docker-compose.yml \
            exec -T odoo rm -f "/tmp/fs_${db}.tar.gz"
        log "  Filestore: $(du -h "$FS_FILE" | cut -f1)"
    else
        log "  Filestore: not found, skipping"
    fi

    BACKUP_COUNT=$((BACKUP_COUNT + 1))
done

# --- Upload to S3 ---------------------------------------------------------
log "Uploading ${BACKUP_COUNT} backups to s3://${S3_BACKUP_BUCKET}/daily/${TIMESTAMP}/"
aws s3 sync "$BACKUP_DIR" "s3://${S3_BACKUP_BUCKET}/daily/${TIMESTAMP}/" \
    --storage-class STANDARD_IA \
    --expected-size 0 \
    --only-show-errors

log "S3 upload complete"

# --- Prune local backups ---------------------------------------------------
log "Pruning local backups older than ${RETENTION_DAYS} days..."
find /opt/backups -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true

# --- Summary ----------------------------------------------------------------
log "=== Backup Complete ==="
log "  Databases: ${BACKUP_COUNT}"
log "  S3 path: s3://${S3_BACKUP_BUCKET}/daily/${TIMESTAMP}/"
log "  Local retention: ${RETENTION_DAYS} days"

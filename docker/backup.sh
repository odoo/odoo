#!/bin/bash
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONTAINER="rkpos-postgres-1"
DB_USER="odoo"
DB_NAME="odoo-db"
ODOO_VOLUME="rkpos_odoo_data"
BACKUP_DIR="/opt/rkadmin/backups"
GD_REMOTE="gdrive:rkpos-backups/club26"   # rclone remote name + Google Drive folder
KEEP_DAYS=7
# ─────────────────────────────────────────────────────────────────────────────

DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_FILE="odoo-backup-${DATE}.tar.gz"
TMP_DIR=$(mktemp -d)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"

log "Starting Odoo backup: ${BACKUP_FILE}"

# 1. Dump PostgreSQL
log "Dumping database ${DB_NAME}..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "${TMP_DIR}/database.sql.gz"

# 2. Archive Odoo filestore via temporary container (avoids root-only volume path)
log "Archiving filestore..."
docker run --rm \
  -v "${ODOO_VOLUME}:/data:ro" \
  -v "${TMP_DIR}:/backup" \
  alpine tar czf /backup/filestore.tar.gz -C /data .

# 3. Bundle into single archive
log "Bundling..."
tar czf "${BACKUP_DIR}/${BACKUP_FILE}" -C "$TMP_DIR" database.sql.gz filestore.tar.gz

SIZE=$(du -sh "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${SIZE})"

# 4. Upload to Google Drive
log "Uploading to Google Drive (${GD_REMOTE})..."
rclone copy "${BACKUP_DIR}/${BACKUP_FILE}" "$GD_REMOTE" --log-level INFO

# 5. Remove local backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "odoo-backup-*.tar.gz" -mtime "+${KEEP_DAYS}" -delete

# 6. Remove old Google Drive backups older than KEEP_DAYS
rclone delete "$GD_REMOTE" --min-age "${KEEP_DAYS}d" --include "odoo-backup-*.tar.gz"

log "Done. Remote backups kept: $(rclone lsf "$GD_REMOTE" --include "odoo-backup-*.tar.gz" | wc -l)"

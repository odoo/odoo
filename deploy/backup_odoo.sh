#!/bin/bash
# Backup diário do Odoo (banco + filestore) → /opt/odoo/backups
set -euo pipefail

DB_NAME="odoo_prod"
DB_USER="odoo"
BACKUP_DIR="/opt/odoo/backups"
FILESTORE="/opt/odoo/data/filestore/${DB_NAME}"
KEEP_DAYS=14

DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

export PATH="/usr/pgsql-15/bin:$PATH"
export PGPASSWORD="Alex2201@"

# Dump do banco
pg_dump -U "$DB_USER" -h 127.0.0.1 "$DB_NAME" \
    | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"

# Filestore
if [ -d "$FILESTORE" ]; then
    tar -czf "${BACKUP_DIR}/filestore_${DATE}.tar.gz" -C "$(dirname "$FILESTORE")" "$(basename "$FILESTORE")"
fi

# Remove backups antigos
find "$BACKUP_DIR" -name "*.gz" -mtime +${KEEP_DAYS} -delete

echo "[$(date)] Backup concluído: db_${DATE}.sql.gz"

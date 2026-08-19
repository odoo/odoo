#!/usr/bin/env bash
# =============================================================================
# sync-filestore-to-s3.sh — Sync local filestore to S3 attachments bucket
#
# Used for:
#   1. Initial migration: sync existing local filestore to S3 before
#      enabling the s3_storage addon.
#   2. Periodic reconciliation: catch any files written locally during
#      the transition period.
#
# Usage:
#   ./scripts/sync-filestore-to-s3.sh                    # sync default path
#   ./scripts/sync-filestore-to-s3.sh /path/to/filestore  # custom path
#
# Requires:
#   - AWS CLI v2 installed
#   - S3_BACKUP_BUCKET env var or --bucket flag
#   - EC2 instance profile with s3:PutObject on the attachments bucket
#
# This script is idempotent — safe to run multiple times. AWS S3 sync
# only uploads files that differ (size or last-modified comparison).
# =============================================================================
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- Config ----------------------------------------------------------------
S3_BUCKET="${S3_ATTACHMENTS_BUCKET:-}"
FILESTORE_PATH="${1:-/var/lib/odoo/filestore}"
EXCLUDE_PATTERNS="*.log,*.tmp,*.swp"

if [ -z "$S3_BUCKET" ]; then
    log "ERROR: S3_ATTACHMENTS_BUCKET not set"
    log "Usage: S3_ATTACHMENTS_BUCKET=my-bucket $0 [filestore-path]"
    exit 1
fi

if [ ! -d "$FILESTORE_PATH" ]; then
    log "ERROR: Filestore directory not found: $FILESTORE_PATH"
    exit 1
fi

# --- Sync -------------------------------------------------------------------
log "Syncing filestore to s3://${S3_BUCKET}/"
log "  Source: ${FILESTORE_PATH}"
log "  Destination: s3://${S3_BUCKET}/"

# Exclude temp/log files
EXCLUDE_ARGS=""
IFS=',' read -ra PATTERNS <<< "$EXCLUDE_PATTERNS"
for pattern in "${PATTERNS[@]}"; do
    EXCLUDE_ARGS="${EXCLUDE_ARGS} --exclude ${pattern}"
done

# shellcheck disable=SC2086
aws s3 sync "$FILESTORE_PATH" "s3://${S3_BUCKET}/" \
    --storage-class STANDARD_IA \
    --only-show-errors \
    $EXCLUDE_ARGS

SYNC_EXIT=$?

if [ $SYNC_EXIT -eq 0 ]; then
    log "=== Sync Complete ==="
    log "  Filestore: ${FILESTORE_PATH}"
    log "  Bucket: s3://${S3_BUCKET}/"
else
    log "ERROR: S3 sync failed with exit code ${SYNC_EXIT}"
    exit $SYNC_EXIT
fi

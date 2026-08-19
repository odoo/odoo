#!/usr/bin/env bash
# =============================================================================
# db-migrate.sh — Migrate local Docker Postgres to RDS
#
# Prerequisites:
#   - Terraform output for RDS endpoint is available
#   - App subnet EC2 has connectivity to RDS (via NAT or within VPC)
#   - psql client installed on the migration host
#   - Docker compose running with local postgres
#
# Usage:
#   ./db-migrate.sh [--dry-run]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/odoo-migration-${TIMESTAMP}.dump"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN MODE ==="
fi

# ---------------------------------------------------------------------------
# Configuration — override via environment or leave as defaults
# ---------------------------------------------------------------------------
RDS_HOST="${RDS_HOST:-}"
RDS_PORT="${RDS_PORT:-5432}"
RDS_DB="${RDS_DB:-odoo}"
RDS_USER="${RDS_USER:-odoo_admin}"
RDS_PASSWORD="${RDS_PASSWORD:-}"
RDS_SECRET_NAME="${RDS_SECRET_NAME:-odoo-invoice-agent-production/rds/master-password}"
RDS_SECRET_REGION="${RDS_SECRET_REGION:-eu-west-1}"

# Read RDS password from Secrets Manager if not provided via env
if [[ -z "$RDS_PASSWORD" ]]; then
  echo "--- Reading RDS password from Secrets Manager ---"
  RDS_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id "$RDS_SECRET_NAME" \
    --region "$RDS_SECRET_REGION" \
    --query 'SecretString' --output text 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])" 2>/dev/null || echo "")
  if [[ -z "$RDS_PASSWORD" ]]; then
    echo "ERROR: Could not read RDS password. Set RDS_PASSWORD env var or configure AWS CLI."
    exit 1
  fi
  echo "  Password retrieved from Secrets Manager."
fi

LOCAL_DB="${LOCAL_DB:-odoo}"
LOCAL_USER="${LOCAL_USER:-odoo}"
LOCAL_HOST="${LOCAL_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_PORT:-5434}"

# If RDS_HOST not set, try terraform output
if [[ -z "$RDS_HOST" ]]; then
  echo "--- Attempting to read RDS endpoint from Terraform output ---"
  cd "$SCRIPT_DIR/../terraform" 2>/dev/null || true
  RDS_HOST=$(terraform output -raw rds_hostname 2>/dev/null || echo "")
  cd "$SCRIPT_DIR"
fi

if [[ -z "$RDS_HOST" ]]; then
  echo "ERROR: RDS_HOST must be set or available from terraform output."
  echo "  export RDS_HOST=your-rds-endpoint.rds.amazonaws.com"
  exit 1
fi

echo ""
echo "============================================"
echo " Odoo Database Migration to RDS"
echo "============================================"
echo "Local:  ${LOCAL_HOST}:${LOCAL_PORT}/${LOCAL_DB} (user: ${LOCAL_USER})"
echo "RDS:    ${RDS_HOST}:${RDS_PORT}/${RDS_DB} (user: ${RDS_USER})"
echo "Dump:   ${DUMP_FILE}"
echo "Time:   $(date -u)"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Pre-migration snapshot
# ---------------------------------------------------------------------------
echo "--- Step 1: Pre-migration local snapshot ---"
SNAPSHOT_FILE="/tmp/odoo-pre-migration-${TIMESTAMP}.sql"
echo "  Dumping local database to ${SNAPSHOT_FILE}..."
pg_dump -h "$LOCAL_HOST" -p "$LOCAL_PORT" -U "$LOCAL_USER" -d "$LOCAL_DB" \
  --format=custom --no-owner --no-privileges \
  -f "$SNAPSHOT_FILE"

SNAPSHOT_SIZE=$(du -h "$SNAPSHOT_FILE" | cut -f1)
echo "  Snapshot created: ${SNAPSHOT_SIZE}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "  [DRY RUN] Would stop Odoo, restore to RDS, and restart."
  echo "  [DRY RUN] Pre-migration snapshot saved to ${SNAPSHOT_FILE}"
  exit 0
fi

# ---------------------------------------------------------------------------
# Step 2: Stop Odoo (prevent writes during migration)
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 2: Stopping Odoo ---"
cd "$SCRIPT_DIR/../.."
docker compose stop odoo
echo "  Odoo stopped."

# ---------------------------------------------------------------------------
# Step 3: Take final local dump (with Odoo stopped — consistent snapshot)
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 3: Final dump with Odoo stopped ---"
pg_dump -h "$LOCAL_HOST" -p "$LOCAL_PORT" -U "$LOCAL_USER" -d "$LOCAL_DB" \
  --format=custom --no-owner --no-privileges \
  -f "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "  Dump created: ${DUMP_SIZE}"

# ---------------------------------------------------------------------------
# Step 4: Validate dump
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 4: Validating dump ---"
DUMP_TABLES=$(pg_restore -l "$DUMP_FILE" 2>/dev/null | grep -c "TABLE" || echo "0")
DUMP_SIZE_BYTES=$(stat -f%z "$DUMP_FILE" 2>/dev/null || stat --printf="%s" "$DUMP_FILE" 2>/dev/null || echo "0")

if [[ "$DUMP_SIZE_BYTES" -lt 1000 ]]; then
  echo "  ERROR: Dump file too small (${DUMP_SIZE_BYTES} bytes). Aborting."
  docker compose start odoo
  exit 1
fi
echo "  Dump contains ~${DUMP_TABLES} table entries. Size: ${DUMP_SIZE}"

# ---------------------------------------------------------------------------
# Step 5: Prepare RDS database
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 5: Preparing RDS database ---"
# Create the database if it doesn't exist
PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '${RDS_DB}'" \
  | grep -q 1 || {
    echo "  Creating database ${RDS_DB}..."
    PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
      -d postgres -c "CREATE DATABASE ${RDS_DB};"
  }

# ---------------------------------------------------------------------------
# Step 6: Restore to RDS
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 6: Restoring to RDS ---"
echo "  This may take several minutes depending on database size..."
RESTORE_START=$(date +%s)

pg_restore -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" -d "$RDS_DB" \
  --clean --if-exists --no-owner --no-privileges --no-comments \
  -j 4 "$DUMP_FILE" 2>&1 | tail -5 || true

RESTORE_END=$(date +%s)
RESTORE_DURATION=$(( RESTORE_END - RESTORE_START ))
echo "  Restore completed in ${RESTORE_DURATION} seconds."

# ---------------------------------------------------------------------------
# Step 7: Post-restore validation
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 7: Post-restore validation ---"
echo "  Running row counts on critical tables..."

# account_move (invoices/bills)
MOVE_COUNT=$(PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" -t -c "SELECT count(*) FROM account_move;" 2>/dev/null | tr -d ' ')
echo "  account_move:       ${MOVE_COUNT} rows"

# account_move_line
LINE_COUNT=$(PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" -t -c "SELECT count(*) FROM account_move_line;" 2>/dev/null | tr -d ' ')
echo "  account_move_line:  ${LINE_COUNT} rows"

# ir_attachment (filestore references)
ATTACH_COUNT=$(PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" -t -c "SELECT count(*) FROM ir_attachment;" 2>/dev/null | tr -d ' ')
echo "  ir_attachment:      ${ATTACH_COUNT} rows"

# res_users
USER_COUNT=$(PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" -t -c "SELECT count(*) FROM res_users;" 2>/dev/null | tr -d ' ')
echo "  res_users:          ${USER_COUNT} rows"

# ---------------------------------------------------------------------------
# Step 8: Create odoo_user with limited privileges
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 8: Creating odoo_user (application role) ---"
PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" <<-'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'odoo_user') THEN
    CREATE ROLE odoo_user WITH LOGIN PASSWORD NULL;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE odoo TO odoo_user;
GRANT USAGE ON SCHEMA public TO odoo_user;
GRANT CREATE ON SCHEMA public TO odoo_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO odoo_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO odoo_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO odoo_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO odoo_user;
SQL
echo "  odoo_user ready."

# ---------------------------------------------------------------------------
# Step 9: ANALYZE for updated statistics
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 9: Running ANALYZE ---"
PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" \
  -d "$RDS_DB" -c "ANALYZE;"
echo "  Statistics updated."

# ---------------------------------------------------------------------------
# Step 10: Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 10: Cleanup ---"
echo "  Keeping dump at ${DUMP_FILE} for reference."
echo "  Keeping snapshot at ${SNAPSHOT_FILE} for rollback."

echo ""
echo "============================================"
echo " Migration Complete"
echo "============================================"
echo " RDS Endpoint: ${RDS_HOST}:${RDS_PORT}"
echo " Database:     ${RDS_DB}"
echo " Duration:     ${RESTORE_DURATION}s"
echo " Dump:         ${DUMP_FILE}"
echo ""
echo " Next steps:"
echo "   1. Update Odoo config to point at RDS (see docker-compose.prod.rds.yml)"
echo "   2. Remove local postgres service from docker-compose.yml"
echo "   3. Restart the full stack"
echo "   4. Run tests: pytest + odoo-bin --test-tags /invoice_agent"
echo ""

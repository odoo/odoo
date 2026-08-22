#!/usr/bin/env bash
# =============================================================================
# scripts/fix_collation.sh — one-time collation version repair
#
# WHY THIS EXISTS
# ---------------
# The db data volume was initialized under a trixie-based Postgres image
# (glibc 2.41), but the floating `pgvector/pgvector:pg16` tag later resolved
# to a bookworm build (glibc 2.36). Every connection then warned:
#
#   WARNING: database "X" has a collation version mismatch
#   DETAIL: The database was created using collation version 2.41, but the
#           operating system provides version 2.36.
#
# A mismatch is not cosmetic: btree indexes over libc-collated text columns
# are ordered according to the collation they were built under. After the OS
# collation changes, those indexes can return wrongly-ordered (and in edge
# cases wrong) results. `ALTER DATABASE ... REFRESH COLLATION VERSION` only
# silences the warning — it does NOT fix the indexes.
#
# WHAT THIS SCRIPT DOES
# ---------------------
# For every database in the cluster (including postgres and template1):
#   1. REINDEX DATABASE  — rebuilds every index under the CURRENT glibc.
#   2. ALTER DATABASE ... REFRESH COLLATION VERSION — records the new
#      collation version so the warnings stop.
# Then it re-verifies that no mismatches remain.
#
# WHEN TO RUN IT
# --------------
# Run ONCE on the EC2 host after switching to the pinned image
# (pgvector/pgvector:0.8.6-pg16-bookworm@sha256:ccc6e83d...):
#
#   cd /opt/odoo && bash scripts/fix_collation.sh
#
# It stops odoo/worker/invoice-ai for the duration (REINDEX takes an
# exclusive lock per index; Odoo must not be connected). Expect minutes of
# downtime proportional to database size. Re-run is safe/idempotent.
#
# Also run this script whenever you deliberately change the db image's base
# OS again (see the PINNED comment in docker-compose.yml).
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Collation repair started at $(date) ==="

# -----------------------------------------------------------------------------
# 1. Stop app containers so nothing holds connections during REINDEX
# -----------------------------------------------------------------------------
echo "Stopping application containers..."
docker compose stop odoo worker invoice-ai || true

# Wait for db healthcheck before touching it
until docker compose exec -T db pg_isready -U "${POSTGRES_USER:-odoo}" -d postgres -q; do
    echo "Waiting for db to be ready..."
    sleep 2
done

# -----------------------------------------------------------------------------
# 2. Repair every non-template database + postgres + template1
# -----------------------------------------------------------------------------
DATABASES=$(docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d postgres -t -A -c \
    "SELECT datname FROM pg_database WHERE datallowconn ORDER BY datname;" | tr -d '\r')

FAILED=0

for DB in $DATABASES; do
    [ -z "$DB" ] && continue
    echo "--- Repairing database: $DB ---"

    # REINDEX DATABASE rebuilds all indexes (incl. system catalogs) under
    # the current libc collation. Plain (non-CONCURRENTLY) form is used:
    # we already stopped all clients, and it is both faster and simpler.
    if ! docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d "$DB" -c "REINDEX DATABASE;"; then
        echo "ERROR: REINDEX failed on database: $DB"
        FAILED=1
        continue
    fi

    if ! docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d "$DB" -c \
        "ALTER DATABASE \"${DB}\" REFRESH COLLATION VERSION;"; then
        echo "ERROR: REFRESH COLLATION VERSION failed on database: $DB"
        FAILED=1
    fi
done

# -----------------------------------------------------------------------------
# 3. Verify: any remaining mismatch means datcollversion != OS collversion
# -----------------------------------------------------------------------------
echo ""
echo "=== Verification ==="
# pg_collation's "default" row carries the collversion of the CURRENT OS
# libc — exactly what datcollversion is compared against when Postgres
# emits its mismatch warning.
MISMATCHES=$(docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d postgres -t -A -c \
    "SELECT d.datname FROM pg_database d WHERE d.datallowconn AND d.datcollversion IS DISTINCT FROM (SELECT c.collversion FROM pg_collation c WHERE c.collname = 'default');" \
    | tr -d '\r' || true)

if [ -n "$MISMATCHES" ]; then
    echo "WARNING: databases still reporting a different collation version:"
    echo "$MISMATCHES"
    FAILED=1
else
    echo "OK — no collation version mismatches remain."
fi

# -----------------------------------------------------------------------------
# 4. Restart application containers
# -----------------------------------------------------------------------------
echo ""
echo "Restarting application containers..."
docker compose up -d odoo worker invoice-ai

echo ""
if [ "$FAILED" -ne 0 ]; then
    echo "=== Collation repair FINISHED WITH ERRORS — review output above ==="
    exit 1
fi
echo "=== Collation repair completed successfully at $(date) ==="

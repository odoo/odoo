#!/bin/bash
set -euo pipefail

replication_password="${REPLICATION_PASSWORD:-${FALLBACK_REPLICATION_PASSWORD:-}}"
if [ -z "${replication_password}" ]; then
  echo "REPLICATION_PASSWORD or FALLBACK_REPLICATION_PASSWORD must be set." >&2
  exit 1
fi

until psql -d postgres -tAc "SELECT 1" >/dev/null 2>&1; do
  sleep 2
done

psql -d postgres -v ON_ERROR_STOP=1 \
  -v replication_user="${REPLICATION_USER}" \
  -v replication_password="${replication_password}" \
  -v replication_slot="${REPLICATION_SLOT}" <<'SQL'
SELECT format(
    'CREATE ROLE %I WITH LOGIN REPLICATION PASSWORD %L',
    :'replication_user',
    :'replication_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'replication_user'
)\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN REPLICATION PASSWORD %L',
    :'replication_user',
    :'replication_password'
)
WHERE EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'replication_user'
)\gexec

SELECT format(
    'SELECT pg_create_physical_replication_slot(%L)',
    :'replication_slot'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_replication_slots
    WHERE slot_name = :'replication_slot'
)\gexec
SQL

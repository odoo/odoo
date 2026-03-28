#!/bin/bash
set -euo pipefail

replication_password="${REPLICATION_PASSWORD:-${FALLBACK_REPLICATION_PASSWORD:-}}"
if [ -z "${replication_password}" ]; then
  echo "REPLICATION_PASSWORD or FALLBACK_REPLICATION_PASSWORD must be set." >&2
  exit 1
fi

if [ ! -s "${PGDATA}/PG_VERSION" ]; then
  rm -rf "${PGDATA:?}/"*

  until PGPASSWORD="${replication_password}" pg_isready -h "${PRIMARY_HOST}" -p "${PRIMARY_PORT}" -U "${REPLICATION_USER}" -d postgres >/dev/null 2>&1; do
    sleep 2
  done

  PGPASSWORD="${replication_password}" pg_basebackup \
    -h "${PRIMARY_HOST}" \
    -p "${PRIMARY_PORT}" \
    -U "${REPLICATION_USER}" \
    -D "${PGDATA}" \
    -R \
    -X stream \
    -S "${REPLICATION_SLOT}" \
    -P

fi

chown -R postgres:postgres "${PGDATA}"
chmod 0700 "${PGDATA}"

exec gosu postgres postgres -c hot_standby=on

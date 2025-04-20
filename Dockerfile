#!/bin/bash
set -e

# Wait until Postgres is accepting connections
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U postgres; do
  echo "Waiting for PostgreSQL at ${PGHOST}:${PGPORT}…"
  sleep 2
done

# Create odoo_user if it doesn't already exist
psql -v ON_ERROR_STOP=1 -U postgres -h "${PGHOST}" -p "${PGPORT}" -d postgres <<-EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_catalog.pg_user WHERE usename = 'odoo_user'
  ) THEN
    CREATE USER odoo_user WITH PASSWORD 'shuwafF2016';
    ALTER USER odoo_user CREATEDB;
  END IF;
END
\$\$;
EOSQL

# Finally, launch Odoo
exec "$@"

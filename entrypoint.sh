#!/bin/bash

# Wait for PostgreSQL to be ready
until pg_isready -h $PGHOST -p $PGPORT -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Create odoo_user if it doesn't exist
psql -U postgres -h $PGHOST -p $PGPORT -d postgres -c "
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'odoo_user') THEN
    CREATE USER odoo_user WITH PASSWORD 'shuwafF2016';
    ALTER USER odoo_user CREATEDB;
  END IF;
END \$\$;"

# Start Odoo
exec odoo -c /etc/odoo/odoo.conf

#!/bin/bash
# Odoo 14 Database Initialization Script

cd /workspaces/odoo

echo "=== Odoo 14 Database Initialization ==="
echo ""

# Start PostgreSQL if not running
if ! docker ps | grep -q odoo-postgres; then
    echo "Starting PostgreSQL in Docker..."
    docker start odoo-postgres 2>/dev/null || docker run -d --name odoo-postgres \
        -e POSTGRES_USER=odoo14 \
        -e POSTGRES_PASSWORD=odoo14 \
        -e POSTGRES_DB=odoo14 \
        -p 5433:5432 \
        postgres:14
    sleep 3
fi

# Drop and recreate database
echo "Creating fresh database..."
docker exec odoo-postgres psql -U odoo14 -d postgres -c "DROP DATABASE IF EXISTS odoo14;"
docker exec odoo-postgres psql -U odoo14 -d postgres -c "CREATE DATABASE odoo14;"

# Initialize Odoo with base and HR modules
echo "Initializing Odoo database (this may take a few minutes)..."
echo ""
PYTHONDONTWRITEBYTECODE=1 python3 odoo-bin -c odoo.conf -d odoo14 \
    --init=base,hr --without-demo=all --stop-after-init

echo ""
echo "=== Initialization Complete ==="
echo "You can now start Odoo with: ./start-odoo.sh"

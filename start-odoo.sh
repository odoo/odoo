#!/bin/bash
# Odoo 14 Startup Script for GitHub Codespace
# This script starts PostgreSQL in Docker and then Odoo

cd /workspaces/odoo

echo "=== Odoo 14 Startup Script ==="
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
    echo "PostgreSQL started on port 5433"
else
    echo "PostgreSQL already running"
fi

echo ""
echo "Starting Odoo 14..."
echo "URL: http://localhost:8069"
echo "Master password: admin"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start Odoo
python3 odoo-bin -c odoo.conf --http-port=8069

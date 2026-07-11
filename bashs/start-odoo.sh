#!/bin/bash
# Start Odoo server with dev helpers (autoreload, qweb, werkzeug, xml)

set -e

cd "$(dirname "$0")"

if [ ! -f "venv/Scripts/python.exe" ]; then
    echo "Error: virtualenv not found at venv/Scripts/python.exe"
    exit 1
fi

if [ ! -f "config/odoo.conf" ]; then
    echo "Error: config file not found at config/odoo.conf"
    exit 1
fi

echo "Starting Odoo server..."
echo "Access at http://localhost:8069"
echo "Press Ctrl+C to stop"
echo ""

./venv/Scripts/python.exe odoo-bin -c config/odoo.conf --dev=reload,qweb,werkzeug,xml

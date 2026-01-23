#!/bin/bash
# PostgreSQL Setup Script for Odoo 14 on GitHub Codespace
# Run this once to set up the database

echo "Setting up PostgreSQL for Odoo 14..."
echo ""
echo "Due to GitHub Codespace security restrictions, you may need to:"
echo "1. Run: sudo -u postgres createuser --superuser codespace"
echo "2. Run: sudo -u postgres createdb -O codespace odoo14"
echo ""
echo "Alternatively, configure PostgreSQL to allow trust authentication:"
echo "1. Edit /etc/postgresql/16/main/pg_hba.conf as root"
echo "2. Change 'peer' to 'trust' for local connections"
echo "3. Run: sudo service postgresql restart"
echo ""
echo "Current odoo.conf uses db_user=codespace with peer authentication"

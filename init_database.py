#!/usr/bin/env python3
"""Script to initialize Odoo database"""
import sys
import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config

# Parse command line arguments
if len(sys.argv) < 2:
    print("Usage: python init_database.py <database_name>")
    sys.exit(1)

db_name = sys.argv[1]

# Load configuration
config.parse_config(['-c', 'odoo.conf'])

# Initialize database
print(f"Initializing database: {db_name}")
print("This may take a few minutes...")

try:
    # Create database if it doesn't exist
    import odoo.service.db as db
    if not db.db_connect(db_name).closed:
        print(f"Database {db_name} already exists")
    else:
        print(f"Creating database {db_name}...")
        db.exp_create_database(db_name, 'en_US', 'admin')
    
    # Install base module
    print("Installing base module...")
    with odoo.api.Environment.manage():
        env = api.Environment(db.db_connect(db_name).cursor(), SUPERUSER_ID, {})
        module = env['ir.module.module'].search([('name', '=', 'base')])
        if module:
            module.button_immediate_install()
            print("Base module installed successfully!")
    
    print(f"✅ Database {db_name} initialized successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

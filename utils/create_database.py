#!/usr/bin/env python

import sys
import argparse
import os
import psycopg2

sys.path.insert(0, os.getcwd() + "/..")
import odoo
from odoo import api, SUPERUSER_ID
import odoo.service.db
import odoo.tools
from odoo.modules.registry import Registry

MODULES = ["base", "web", "nortk_theme"]


def install_module(env: api.Environment, module_name: str) -> bool:
    """
    Install a module to the odoo database

    Args:
        env: Odoo environment
        module_name: Name of the module to install

    Returns:
        True if the module installed successfully
        False on error
    """

    # 5. INSTALL MODULE
    print(f"Installing module: {module_name}...")
    module = env['ir.module.module'].search([('name', '=', module_name)])

    if module:
        if module.state == 'installed':
            print(f"Module '{module_name}' is already installed.")
        else:
            print(f"Installing '{module_name}'...")
            module.button_immediate_install()
            print("Installation successful.")
        return True
    else:
        print(f"ERROR: Module '{module_name}' not found in the addons path provided.")
        print(f"Current addons path: {odoo.tools.config['addons_path']}")
        return False


def parse_arguments():
    """
    Parse arguments
    """

    parser = argparse.ArgumentParser(description="Automated Odoo Database Setup")

    parser.add_argument('-c', '--config', dest='config', default='/etc/odoo/odoo.conf', help="Path to odoo.conf")
    parser.add_argument("--db", required=True, help="Name of the database to create/update")
    parser.add_argument("--email", required=True, help="New admin email (login)")
    parser.add_argument("--password", required=True, help="New admin password")
    parser.add_argument("--modules", default="pos_restaurant", help="Comma-separated list of modules to install (e.g. sale,stock,nortk_theme)")
    parser.add_argument("--addons", default="./addons,./custom_addons", help="Comma-separated paths to addons directories")

    return parser.parse_args()



def preflight_check(db_name, args):
    """
    Verifies direct connection to Postgres before Odoo starts, on error
    exits the program.

    Args:
        db_name: Database name
        args: Command line arguments

    """

    db_host = args.get("db_host") 
    db_port = port=args.get("db_port")
    print(f"--- 1. Pre-flight: Testing Connection to '{db_host}:{db_port}' ---")

    try:
        # Connect to 'postgres' database to check credentials
        conn = psycopg2.connect(
            dbname=db_name, 
            user=args.get("db_user"), 
            password=args.get("db_password"), 
            host=db_host, 
            port=db_port
        )
        conn.close()
        print("SUCCESS: Credentials are valid and Server is reachable.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: Cannot connect to PostgreSQL.")
        print(f"Error details: {e}")
        print("\nDouble check your --db_user and --db_password.")
        sys.exit(1)



def main():
    args = parse_arguments()

    print(f"--- Starting Setup for Database: {args.db} ---")

    config_args = ['--addons-path', args.addons]

    if args.config:
        config_args.extend(['-c', args.config])

    # Now Odoo reads the DB host/user/pass from your conf file
    odoo.tools.config.parse_config(config_args)

    #DEBUG enable for DB check preflight_check(args.db, odoo.tools.config.options)

    if not odoo.service.db.exp_db_exist(args.db):
        print(f"Creating database '{args.db}'...")
        try:
            # exp_create_database(db_name, demo_data, language, admin_password)
            #odoo.service.db.exp_create_database(args.db, False, 'es_MX.UTF-8', 'admin')
            odoo.service.db.exp_create_database(args.db, False, 'es_MX', 'admin')
            print("Database created.")
        except Exception as e:
            print(f"FAILED to create database: {e}")
            sys.exit(1)
    else:
        print(f"Database '{args.db}' already exists. Connecting...")

    registry = Registry(args.db)
    if not registry:
        print(f"Could not initialize registry for database: {args.db}")
        sys.exit(1)

    print(f"Successfully loaded registry for database: {args.db}")

    with registry.cursor() as cr:
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # 4. UPDATE ADMIN CREDENTIALS
            print(f"Updating admin credentials to {args.email}...")
            admin_user = env.ref('base.user_admin')
            admin_user.write({
                'login': args.email,
                'email': args.email,
                'password': args.password
            })

            # Install basic modules
            for m in MODULES:
                install_module(env, m)

            # 5. INSTALL MODULE
            print(f"Checking module: {args.module}...")
            if not install_module(env, args.module):
                sys.exit()

        except Exception as e:
            print(f"An error occurred during transaction: {e}")
            # The cursor context manager usually rolls back on error, but explicit logging helps.
            sys.exit(1)

    print("--- Setup Finished Successfully ---")

if __name__ == "__main__":
    main()

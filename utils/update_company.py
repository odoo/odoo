#!/bin/python

import odoo
from odoo import api
from odoo import tools
from odoo.modules.registry import Registry

import sys
import logging
import base64
import os

# --- Configuration: UPDATE THESE VALUES ---
CONFIG_FILE = "utils/config/odoo.conf"
DB_NAME = "pos_test"

# --- New Company Details ---
NEW_COMPANY_NAME = "Prueba de POS"
NEW_LOGO_PATH = "/home/imcsk8/Imágenes/don_burro/db_logo-01.png"
# ------------------------------------------

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

def update_company_details():
    # --- 1. Check if Logo File Exists ---
    if not os.path.isfile(NEW_LOGO_PATH):
        _logger.error(f"Logo file not found at: {NEW_LOGO_PATH}")
        _logger.error("Please check the NEW_LOGO_PATH variable in the script.")
        sys.exit(1)

    # --- 2. Load Odoo Configuration ---
    try:
        tools.config.parse_config(['-c', CONFIG_FILE])
    except FileNotFoundError:
        _logger.error(f"Configuration file not found: {CONFIG_FILE}")
        sys.exit(1)

    # --- 3. Get Registry ---
    registry = Registry(DB_NAME)
    if not registry:
        _logger.error(f"Could not initialize registry for database: {DB_NAME}")
        sys.exit(1)

    _logger.info(f"Successfully loaded registry for database: {DB_NAME}")

    # --- 4. Start Transaction ---
    # Use a 'with' block for transaction management
    # We run as the admin user (UID=1) for full permissions
    with registry.cursor() as cr:
        # Create an Odoo environment
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})

        try:
            # --- 5. Find the Main Company ---
            # 'base.main_company' is the XML ID for the default company
            main_company = env.ref('base.main_company')
            if not main_company:
                _logger.error("Could not find 'base.main_company'.")
                raise Exception("Main company not found.")

            _logger.info(f"Found company to update: {main_company.name} (ID: {main_company.id})")

            # --- 6. Read and Encode the Logo ---
            logo_base64 = None
            with open(NEW_LOGO_PATH, 'rb') as logo_file:
                logo_data = logo_file.read()
                logo_base64 = base64.b64encode(logo_data)

            if not logo_base64:
                raise Exception("Could not read or encode logo file.")

            _logger.info(f"Successfully encoded logo from {NEW_LOGO_PATH}")

            # --- 7. Prepare Values and Write to DB ---
            vals_to_write = {
                'name': NEW_COMPANY_NAME,
                'logo': logo_base64,
            }

            main_company.write(vals_to_write)

        except Exception as e:
            # If any error occurs, roll back the transaction
            _logger.error(f"An error occurred: {e}. Rolling back transaction.")
            env.cr.rollback()
            sys.exit(1)
        else:
            # --- 8. Commit Transaction ---
            # If no errors, commit the changes
            env.cr.commit()
            _logger.info("--- Company Update Complete! ---")
            _logger.info(f"Company name successfully changed to: {NEW_COMPANY_NAME}")
            _logger.info("Company logo has been updated.")

# Main execution
if __name__ == "__main__":
    update_company_details()

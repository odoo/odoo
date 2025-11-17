#!/bin/python


import sys
import argparse
import logging
import os
import csv

sys.path.insert(0, os.getcwd() + "/..")
# Odoo stuff
import odoo
from odoo import api
from odoo import tools
from odoo.modules.registry import Registry
# ------------------------------

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Odoo Product Import from CSV")

    # Connection Args
    parser.add_argument('-c', '--config', dest='config', default='/etc/odoo/odoo.conf', help="Path to odoo.conf")
    parser.add_argument('-d', '--db', dest='db', required=True, help="Database name")
    # File Arg
    parser.add_argument('-f', '--file', dest='csv_file', required=True, help="Path to the input CSV file")

    args = parser.parse_args()

    # 1. Verify File Exists
    if not os.path.isfile(args.csv_file):
        _logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)

    # 2. Initialize Odoo
    try:
        tools.config.parse_config(['-c', args.config])
        registry = Registry(args.db)
    except Exception as e:
        _logger.error(f"Error initializing Odoo: {e}")
        sys.exit(1)

    _logger.info(f"Connected to database: {args.db}")

    # 3. Process Data
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        Product = env['product.product']
        Category = env['product.category']
        Uom = env['uom.uom']

        created_count = 0

        try:
            with open(args.csv_file, 'r', encoding='utf-8') as f:
                # Use colon delimiter as requested
                reader = csv.DictReader(f, delimiter=':')

                for row in reader:
                    # Clean whitespace from keys and values (handle " : " spaces)
                    clean_row = {k.strip(): v.strip() for k, v in row.items()}

                    # --- Extract Data ---
                    name = clean_row.get('description')
                    uom_name = clean_row.get('unit_measure')
                    categ_name = clean_row.get('category')

                    # Numeric Conversions
                    try:
                        qty_per_pkg = float(clean_row.get('quantity_per_package', 0))
                        pkg_price = float(clean_row.get('package_price', 0))
                        weight = float(clean_row.get('bottle_weight', 0))
                    except ValueError:
                        _logger.warning(f"Skipping invalid row (number error): {name}")
                        continue

                    # Calculate Unit Price (Price / Qty)
                    unit_price = pkg_price / qty_per_pkg if qty_per_pkg > 0 else 0.0

                    # --- Resolve Relations ---

                    # 1. Category (Find or Create)
                    categ = Category.search([('name', '=', categ_name)], limit=1)
                    if not categ and categ_name:
                        categ = Category.create({'name': categ_name})
                        _logger.info(f"Created new Category: {categ_name}")

                    # 2. Unit of Measure (Find)
                    # Search for UoM by name (e.g., "Pz"). If not found, defaults to None (Odoo uses default)
                    uom = Uom.search([('name', '=', uom_name)], limit=1)

                    # --- Create Product ---
                    vals = {
                        'name': name,
                        'list_price': unit_price, # Sale price per unit
                        'weight': weight,
                        'type': 'consu', # 'consu' = Storable Product
                    }

                    print(f"Creating producto: {vals}\n")

                    if categ:
                        vals['categ_id'] = categ.id
                    if uom:
                        vals['uom_id'] = uom.id
                        vals['uom_po_id'] = uom.id # Set Purchase UoM same as Sale UoM

                    Product.create(vals)
                    created_count += 1
                    _logger.info(f"Staged: {name} | Unit Price: ${unit_price:.2f}")

        except Exception as e:
            _logger.error(f"Import failed: {e}")
            env.cr.rollback()
            sys.exit(1)
        else:
            env.cr.commit()
            _logger.info(f"--- Success: Imported {created_count} products ---")

if __name__ == "__main__":
    main()

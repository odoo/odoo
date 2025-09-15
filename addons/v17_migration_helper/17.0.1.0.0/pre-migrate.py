# -*- coding: utf-8 -*-
"""
Migration script for Odoo v16 to v17 upgrade
Removes incompatible modules and fixes template references

File location: addons/your_module/migrations/17.0.1.0.0/pre-migrate.py
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration function called during module upgrade
    
    Args:
        cr: Database cursor
        version: Current version being migrated to
    """
    _logger.info("Starting v16 to v17 migration cleanup...")
    
    # List of incompatible modules to remove
    modules_to_remove = [
        'app_product_superbar', 
        'bi_sales_invoice_details', 
        'list_view_sticky_header', 
        'mail_from_contacts',
        'product_variant_sale_price', 
        'receipt_status_in_po_and_bills',
        'web_chatter_position', 
        'web_sheet_full_width'
    ]
    
    try:
        # Step 1: Mark incompatible modules as uninstalled
        _logger.info("Marking incompatible modules as uninstalled...")
        
        if modules_to_remove:
            module_names = "','".join(modules_to_remove)
            cr.execute(f"""
                UPDATE ir_module_module 
                SET state = 'uninstalled' 
                WHERE name IN ('{module_names}')
                AND state != 'uninstalled'
            """)
            
            affected_rows = cr.rowcount
            _logger.info(f"Marked {affected_rows} modules as uninstalled")
        
        # Step 2: Fix views with chatter_position references
        _logger.info("Fixing views with chatter_position references...")
        
        # Find views with chatter_position references
        cr.execute("""
            SELECT id, name, key, arch_db
            FROM ir_ui_view 
            WHERE arch_db::text ILIKE '%chatter_position%'
        """)
        
        problematic_views = cr.fetchall()
        _logger.info(f"Found {len(problematic_views)} views with chatter_position references")
        
        fixed_count = 0
        for view_id, view_name, view_key, arch_db in problematic_views:
            try:
                # Convert arch_db to string
                arch_str = str(arch_db) if arch_db else ""
                original_arch = arch_str
                
                # Apply the proven replacements
                arch_str = arch_str.replace('<t t-out="request.env.user.chatter_position"/>', '')
                arch_str = arch_str.replace('t-out="request.env.user.chatter_position"', 't-out="false"')
                arch_str = arch_str.replace('request.env.user.chatter_position', 'false')
                
                # Only update if changes were made
                if arch_str != original_arch:
                    cr.execute("""
                        UPDATE ir_ui_view 
                        SET arch_db = %s::jsonb
                        WHERE id = %s
                    """, (arch_str, view_id))
                    
                    fixed_count += 1
                    _logger.info(f"Fixed view: {view_name} (ID: {view_id})")
                
            except Exception as e:
                _logger.warning(f"Failed to fix view {view_name} (ID: {view_id}): {e}")
        
        _logger.info(f"Successfully fixed {fixed_count} views")
        
        # Step 3: Clean up residual data
        _logger.info("Cleaning up residual data...")
        
        # Remove model data from problematic modules
        if modules_to_remove:
            module_names = "','".join(modules_to_remove)
            cr.execute(f"""
                DELETE FROM ir_model_data 
                WHERE module IN ('{module_names}')
            """)
            deleted_data = cr.rowcount
            _logger.info(f"Removed {deleted_data} model data records")
        
        # Remove chatter_position field definitions
        cr.execute("""
            DELETE FROM ir_model_fields 
            WHERE model = 'res.users' AND name = 'chatter_position'
        """)
        deleted_fields = cr.rowcount
        if deleted_fields:
            _logger.info(f"Removed {deleted_fields} chatter_position field definitions")
        
        # Remove module dependencies
        if modules_to_remove:
            module_names = "','".join(modules_to_remove)
            cr.execute(f"""
                DELETE FROM ir_module_module_dependency 
                WHERE name IN ('{module_names}')
            """)
            deleted_deps = cr.rowcount
            if deleted_deps:
                _logger.info(f"Removed {deleted_deps} module dependency records")
        
        # Step 4: Remove chatter_position column from database if it exists
        _logger.info("Removing chatter_position column from res_users table...")
        try:
            cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS chatter_position")
            _logger.info("Successfully dropped chatter_position column")
        except Exception as e:
            _logger.warning(f"Could not drop chatter_position column: {e}")
        
        _logger.info("Migration cleanup completed successfully!")
        
    except Exception as e:
        _logger.error(f"Migration failed with error: {e}")
        raise
# File: addons/your_custom_module/__manifest__.py
{
    'name': 'V17 Migration Helper',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Migration helper for v16 to v17 upgrade',
    'description': 'Migration helper module for upgrading from Odoo v16 to v17. Removes incompatible modules and fixes template references.',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# File: addons/your_custom_module/migrations/17.0.1.0.0/pre-migrate.py
# -*- coding: utf-8 -*- 

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):

    _logger.info("=== PRE-MIGRATION: Starting v16 to v17 cleanup ===")
    
    # Your migration code here (from the previous artifact)
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
        # Mark incompatible modules as uninstalled
        _logger.info("Marking incompatible modules as uninstalled...")
        
        if modules_to_remove:
            placeholders = ','.join(['%s'] * len(modules_to_remove))
            cr.execute(f"""
                UPDATE ir_module_module 
                SET state = 'uninstalled' 
                WHERE name IN ({placeholders})
                AND state != 'uninstalled'
            """, modules_to_remove)
            
            affected_rows = cr.rowcount
            _logger.info(f"Marked {affected_rows} modules as uninstalled")
        
        # Fix views with chatter_position references
        _logger.info("Fixing views with chatter_position references...")
        
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
                arch_str = str(arch_db) if arch_db else ""
                original_arch = arch_str
                
                # Apply your proven replacements
                arch_str = arch_str.replace('<t t-out="request.env.user.chatter_position"/>', '')
                arch_str = arch_str.replace('t-out="request.env.user.chatter_position"', 't-out="false"')
                arch_str = arch_str.replace('request.env.user.chatter_position', 'false')
                
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
        
        # Clean up residual data
        _logger.info("Cleaning up residual data...")
        
        if modules_to_remove:
            placeholders = ','.join(['%s'] * len(modules_to_remove))
            cr.execute(f"""
                DELETE FROM ir_model_data 
                WHERE module IN ({placeholders})
            """, modules_to_remove)
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
            placeholders = ','.join(['%s'] * len(modules_to_remove))
            cr.execute(f"""
                DELETE FROM ir_module_module_dependency 
                WHERE name IN ({placeholders})
            """, modules_to_remove)
            deleted_deps = cr.rowcount
            if deleted_deps:
                _logger.info(f"Removed {deleted_deps} module dependency records")
        
        # Remove chatter_position column from database
        _logger.info("Removing chatter_position column from res_users table...")
        try:
            cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS chatter_position")
            _logger.info("Successfully dropped chatter_position column")
        except Exception as e:
            _logger.warning(f"Could not drop chatter_position column: {e}")
        
        _logger.info("=== PRE-MIGRATION: Cleanup completed successfully ===")
        
    except Exception as e:
        _logger.error(f"Pre-migration failed with error: {e}")
        raise


# File: addons/your_custom_module/migrations/17.0.1.0.0/post-migrate.py
# -*- coding: utf-8 -*-


import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):

    _logger.info("=== POST-MIGRATION: Starting v16 to v17 validation ===")
    
    modules_to_check = [
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
        # Validate modules are uninstalled
        _logger.info("Validating module states...")
        
        placeholders = ','.join(['%s'] * len(modules_to_check))
        cr.execute(f"""
            SELECT name, state 
            FROM ir_module_module 
            WHERE name IN ({placeholders})
            AND state != 'uninstalled'
        """, modules_to_check)
        
        still_installed = cr.fetchall()
        
        if still_installed:
            _logger.warning(f"Found {len(still_installed)} modules still not uninstalled:")
            for name, state in still_installed:
                _logger.warning(f"  - {name}: {state}")
        else:
            _logger.info("✓ All target modules are properly uninstalled")
        
        # Check for remaining chatter_position references
        _logger.info("Checking for remaining chatter_position references...")
        
        cr.execute("""
            SELECT COUNT(*) 
            FROM ir_ui_view 
            WHERE arch_db::text ILIKE '%chatter_position%'
        """)
        
        remaining_refs = cr.fetchone()[0]
        
        if remaining_refs:
            _logger.warning(f"Found {remaining_refs} views still containing chatter_position references")
        else:
            _logger.info("✓ No chatter_position references found in views")
        
        # Check field definitions
        cr.execute("""
            SELECT COUNT(*) 
            FROM ir_model_fields 
            WHERE model = 'res.users' AND name = 'chatter_position'
        """)
        
        remaining_fields = cr.fetchone()[0]
        
        if remaining_fields:
            _logger.warning(f"Found {remaining_fields} chatter_position field definitions still exist")
        else:
            _logger.info("✓ No chatter_position field definitions found")
        
        # Final validation summary
        issues = len(still_installed) + (1 if remaining_refs > 0 else 0) + (1 if remaining_fields > 0 else 0)
        
        if issues == 0:
            _logger.info("=== POST-MIGRATION: All validations passed successfully ===")
        else:
            _logger.warning(f"=== POST-MIGRATION: Completed with {issues} validation warnings ===")
        
    except Exception as e:
        _logger.error(f"Post-migration validation failed: {e}")
        raise
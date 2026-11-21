def migrate(cr, version):
    """Ensure legacy view file paths and model data point to the consolidated wizard views."""
    cr.execute("""
        UPDATE ir_ui_view
        SET arch_fs = 'school_public_holiday/wizard/holiday_import_wizard_views.xml'
        WHERE arch_fs LIKE '%public_holiday_import_wizard_views.xml%';
    """)
    cr.execute("""
        UPDATE ir_model_data
        SET name = 'view_wizard_import_public_holiday_form'
        WHERE module = 'school_public_holiday'
          AND name = 'view_public_holiday_import_wizard_form'
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_data
              WHERE module = 'school_public_holiday'
                AND name = 'view_wizard_import_public_holiday_form'
          );
    """)

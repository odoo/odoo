def migrate(cr, version):

    cr.execute("""
        UPDATE ir_model_data
           SET name = 'tax_report'
         WHERE module='l10n_ee' AND name='tax_report_vat'
    """)

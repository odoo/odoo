def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data
           SET noupdate = true
         WHERE module = 'l10n_co_dian'
           AND name IN ('email_template_edi_invoice', 'email_template_edi_credit_note')
    """)

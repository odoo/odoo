def migrate(cr, version):

    cr.execute("""
        UPDATE account_tax
           SET l10n_it_exempt_reason = 'N2.1'
         WHERE l10n_it_exempt_reason = 'N3.2'
           AND sequence = 185
           AND amount = 0.0
           AND type_tax_use = 'sale'
           AND tax_scope = 'service'
    """)

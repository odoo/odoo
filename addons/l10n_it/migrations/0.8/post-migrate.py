def migrate(cr, version):

    cr.execute("""
        UPDATE account_tax
           SET l10n_it_exempt_reason = CASE
               WHEN l10n_it_exempt_reason = 'N2' THEN 'N2.2'
               WHEN l10n_it_exempt_reason = 'N3' THEN 'N3.6'
               WHEN l10n_it_exempt_reason = 'N6' THEN 'N6.9'
               END
          WHERE l10n_it_exempt_reason IN ('N2', 'N3', 'N6')
    """)

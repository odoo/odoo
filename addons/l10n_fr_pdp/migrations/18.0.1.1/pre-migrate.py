def migrate(cr, version):
    cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN l10n_fr_pdp_late_payment_penalties_rate numeric DEFAULT 10.0
    """)
    cr.execute("""
        ALTER TABLE account_move
        ALTER COLUMN l10n_fr_pdp_late_payment_penalties_rate DROP DEFAULT
    """)
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = 'l10n_fr_pdp_penalty_rate'
          AND state = 'uninstalled'
    """)

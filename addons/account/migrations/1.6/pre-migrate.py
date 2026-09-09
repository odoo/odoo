def migrate(cr, version):
    cr.execute("""
        DROP INDEX IF EXISTS account_move_sanitize_payment_ref_idx;
    """)
    cr.execute("""
        CREATE INDEX account_move_sanitize_payment_ref_idx
                  ON account_move (regexp_replace(COALESCE(payment_reference, ref, ''), '[^a-zA-Z0-9]', '', 'g'));
    """)

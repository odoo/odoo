def migrate(cr, version):
    cr.execute(
        """
            UPDATE account_account
               SET code_store = NULL
             WHERE code_store = 'null'::jsonb
        """
    )

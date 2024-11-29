def migrate(cr, version):
    cr.execute(
        """
        WITH banks AS (
            SELECT bank.id,
                   LOWER(bank.bic) AS bic
              FROM res_bank bank
              JOIN ir_model_data d
                ON d.module = 'base'
               AND d.name = 'fr'
               AND d.res_id = bank.country
             WHERE bank.active
               AND bank.bic IS NOT NULL
        )
        INSERT INTO ir_model_data(
                        model,
                        module,
                        name,
                        res_id,
                        noupdate
                    )
             SELECT 'res.bank',
                    'l10n_fr_account',
                    CONCAT('bank_fr_', banks.bic),
                    banks.id,
                    True
               FROM banks
        ON CONFLICT DO NOTHING
        """
    )

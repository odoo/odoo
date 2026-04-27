def migrate(cr, version):
    cr.execute(
        """
        INSERT INTO ir_model_data (res_id, name, module, model, noupdate)
              SELECT l10n.id, l10n.code, 'l10n_at_saft', 'l10n_at_saft.account', True
                FROM l10n_at_saft_account l10n
        ON CONFLICT DO NOTHING
        """
    )

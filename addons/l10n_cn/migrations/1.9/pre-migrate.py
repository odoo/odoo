def migrate(cr, version):
    # Set noupdate property of "account.tax.template" records to False
    cr.execute(
        """UPDATE ir_model_data
              SET noupdate=false
            WHERE module='l10n_cn'
              AND model='account.tax.template'
        """
    )

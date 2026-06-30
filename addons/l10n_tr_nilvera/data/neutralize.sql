-- disable l10n_tr_nilvera integration
UPDATE res_company
   SET l10n_tr_nilvera_api_key = NULL,
       l10n_tr_nilvera_use_test_env = TRUE,
       l10n_tr_nilvera_purchase_journal_id = NULL;

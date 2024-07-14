-- disable l10n_co edi integration
UPDATE res_company
   SET l10n_co_edi_test_mode = true;

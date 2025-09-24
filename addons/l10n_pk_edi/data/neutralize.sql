-- disable l10n_pk_edi integration
UPDATE res_company
   SET l10n_pk_edi_auth_token = NULL;

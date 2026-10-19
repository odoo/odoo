-- disable l10n_pk_edi integration
UPDATE res_company
   SET l10n_pk_edi_production_auth_token = NULL,
       l10n_pk_edi_whitelisted = false;

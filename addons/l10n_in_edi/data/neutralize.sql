-- disable l10n_in_edi integration
UPDATE res_company
   SET l10n_in_edi_username = NULL,
       l10n_in_edi_password = NULL,
       l10n_in_edi_token = NULL,
       l10n_in_edi_token_validity = NULL;

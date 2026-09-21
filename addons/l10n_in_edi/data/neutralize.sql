-- disable l10n_in_edi integration
UPDATE l10n_in_edi_config
   SET l10n_in_edi_username = NULL,
       l10n_in_edi_token_validity = NULL;

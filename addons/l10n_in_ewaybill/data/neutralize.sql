-- disable l10n_in_edi_ewaybill integration
UPDATE l10n_in_ewaybill_config
   SET l10n_in_ewaybill_username = NULL,
       l10n_in_ewaybill_auth_validity = NULL;

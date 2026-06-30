-- disable l10n_in_edi_ewaybill integration
UPDATE res_company
   SET l10n_in_ewaybill_username = NULL,
       l10n_in_ewaybill_password = NULL,
       l10n_in_ewaybill_auth_validity = NULL;

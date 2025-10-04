-- disable l10n_my_edi integration by archiving all proxy users; and reset the mode to pre-production.
UPDATE account_edi_proxy_client_user
   SET active = FALSE
 WHERE proxy_type = 'l10n_my_edi';
UPDATE res_company
   SET l10n_my_edi_mode = 'test';

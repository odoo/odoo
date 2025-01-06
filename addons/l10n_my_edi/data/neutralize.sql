-- disable l10n_my_edi integration by archiving all proxy users.
UPDATE account_edi_proxy_client_user
   SET active = FALSE
 WHERE proxy_type = 'l10n_my_edi'

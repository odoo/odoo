UPDATE account_edi_proxy_client_user
   SET active = FALSE
 WHERE proxy_type = 'l10n_gr_edi';

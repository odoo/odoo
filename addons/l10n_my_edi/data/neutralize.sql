-- disable l10n_my_edi integration by reverting all proxy client to demo mode
UPDATE account_edi_proxy_client_user
   SET edi_mode = 'demo'

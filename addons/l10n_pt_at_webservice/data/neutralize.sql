-- disable the AT webservice and drop its credentials
UPDATE res_company
   SET l10n_pt_at_ws_env = 'offline',
       l10n_pt_at_ws_username = NULL,
       l10n_pt_at_ws_password = NULL
 WHERE l10n_pt_at_ws_env != 'offline'
    OR l10n_pt_at_ws_username IS NOT NULL
    OR l10n_pt_at_ws_password IS NOT NULL;

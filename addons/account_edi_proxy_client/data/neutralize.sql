-- disable edi connections in general, and the Italian one (l10n_it_edi_sdicoop) in particular
UPDATE account_edi_proxy_client_user
SET edi_mode = CASE
                    WHEN proxy_type = 'l10n_it_edi' THEN 'demo'
                    ELSE 'test'
               END;

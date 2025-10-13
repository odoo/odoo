-- disable edi connections in general, and the Italian one (l10n_it_edi_sdicoop) in particular
-- for malaysian edi, this script can cause issue as you could have both a demo and prod user, in which case it breaks the unique constrain. Another neutralize in the malaysian module disable the clients instead.
UPDATE account_edi_proxy_client_user
SET edi_mode = CASE
                    WHEN proxy_type IN ('l10n_it_edi', 'peppol', 'nemhandel') THEN 'demo'
                    ELSE 'test'
               END
WHERE proxy_type != 'l10n_my_edi';

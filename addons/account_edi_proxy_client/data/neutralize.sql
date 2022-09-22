-- disable edi connections in general, and the Italian one (l10n_it_edi_sdicoop) in particular
INSERT INTO ir_config_parameter (key, value)
VALUES ('account_edi_proxy_client.demo', true)
    ON CONFLICT (key) DO
       UPDATE SET value = true;

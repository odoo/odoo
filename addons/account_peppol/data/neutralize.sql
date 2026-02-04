INSERT INTO ir_config_parameter (key, value)
     VALUES ('account_peppol.edi.mode', 'demo')
ON CONFLICT (key) DO UPDATE
        SET VALUE = 'demo';

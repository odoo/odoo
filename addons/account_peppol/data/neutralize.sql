INSERT INTO ir_config_parameter (key, value)
     VALUES ('account_peppol.edi.mode', 'test')
ON CONFLICT (key) DO UPDATE
        SET VALUE = 'test';

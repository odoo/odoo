-- disable voip
INSERT INTO ir_config_parameter (key, value)
VALUES ('voip.mode', 'demo')
    ON CONFLICT (key) DO
       UPDATE SET value = 'demo';

UPDATE ir_config_parameter
SET value = 'dummy_token'
WHERE key = 'iap_vies.client_token';

UPDATE ir_config_parameter
SET value = 'dummy_identifier'
WHERE key = 'iap_vies.client_identifier';

-- Replace official VIES endpoint with test endpoint
INSERT INTO ir_config_parameter (key, value)
VALUES ('iap_vies.endpoint', 'https://vies.test.odoo.com')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
WHERE ir_config_parameter.value = 'https://vies.api.odoo.com';

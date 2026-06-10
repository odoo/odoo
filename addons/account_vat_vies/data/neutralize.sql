UPDATE ir_config_parameter
SET value = 'dummy_token'
WHERE key = 'iap_vies.client_token';

UPDATE ir_config_parameter
SET value = 'dummy_identifier'
WHERE key = 'iap_vies.client_identifier';

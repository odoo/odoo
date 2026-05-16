UPDATE ir_config_parameter
SET value = 'dummy_token'
WHERE key = 'vies_iap.client_token';

UPDATE ir_config_parameter
SET value = 'dummy_identifier'
WHERE key = 'vies_iap.client_identifier';

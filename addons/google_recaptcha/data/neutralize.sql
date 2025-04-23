-- disable reCAPTCHA
UPDATE ir_config_parameter
SET value = ''
WHERE key IN ('recaptcha_public_key', 'recaptcha_private_key');

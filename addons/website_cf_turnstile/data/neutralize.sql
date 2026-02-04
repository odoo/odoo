-- disable cf turnstile 
UPDATE ir_config_parameter
SET value = ''
WHERE key IN ('cf.turnstile_site_key','cf.turnstile_secret_key');

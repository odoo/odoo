-- disable reCAPTCHA
INSERT INTO ir_config_parameter (key, value)
VALUES ('enable_recaptcha', false)
    ON CONFLICT DO NOTHING;

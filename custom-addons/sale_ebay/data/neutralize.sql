-- disable ebay
INSERT INTO ir_config_parameter (key, value)
VALUES
    ('ebay_domain', 'sand'),
    ('ebay_dev_id', 'dummy'),
    ('ebay_prod_token', 'dummy'),
    ('ebay_prod_app_id', 'dummy'),
    ('ebay_prod_cert_id', 'dummy'),
    ('ebay_verification_token', 'dummy'),
    ('ebay_sandbox_token', 'dummy'),
    ('ebay_sandbox_app_id', 'dummy'),
    ('ebay_sandbox_cert_id', 'dummy')
ON CONFLICT (key) DO
    UPDATE SET value = CASE
        WHEN EXCLUDED.key = 'ebay_domain' THEN 'sand'
        ELSE 'dummy'
    END;

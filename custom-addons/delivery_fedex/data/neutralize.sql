-- disable fedex
UPDATE delivery_carrier
SET fedex_developer_key = 'dummy',
    fedex_developer_password = 'dummy';

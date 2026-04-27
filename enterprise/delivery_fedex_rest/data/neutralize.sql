-- disable fedex rest connector
UPDATE delivery_carrier
SET fedex_rest_developer_key = 'dummy',
    fedex_rest_developer_password = 'dummy',
    fedex_rest_account_number = 'dummy',
    fedex_rest_access_token = 'dummy';

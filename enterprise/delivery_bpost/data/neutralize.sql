-- disable bpost
UPDATE delivery_carrier
SET bpost_account_number = 'dummy',
    bpost_developer_password = 'dummy';

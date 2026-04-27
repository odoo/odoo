-- disable dhl
UPDATE delivery_carrier
SET "dhl_api_key" = 'dummy',
    dhl_account_number = 'dummy',
    dhl_api_secret = 'dummy';

-- disable dhl
UPDATE delivery_carrier
SET "dhl_SiteID" = 'dummy',
    dhl_account_number = 'dummy',
    dhl_password = 'dummy';

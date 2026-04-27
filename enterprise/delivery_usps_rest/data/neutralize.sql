-- disable usps
UPDATE delivery_carrier
SET usps_api_key = 'dummy',
    usps_api_secret = 'dummy',
    usps_eps_account_number = 'dummy',
    usps_crid = 'dummy',
    usps_mid = 'dummy',
    usps_manifest_mid = 'dummy',
    usps_access_token = 'dummy',
    usps_payment_token = 'dummy';

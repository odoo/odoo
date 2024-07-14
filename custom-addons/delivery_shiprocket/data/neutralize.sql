-- disable shiprocket
UPDATE delivery_carrier
SET shiprocket_email = 'dummy',
    shiprocket_access_token = 'dummy',
    shiprocket_password = 'dummy';

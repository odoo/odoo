-- disable sendcloud
UPDATE delivery_carrier
SET sendcloud_public_key = 'dummy',
    sendcloud_secret_key = 'dummy';
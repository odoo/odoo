-- disable ups
UPDATE delivery_carrier
SET ups_username = 'dummy',
    ups_passwd = 'dummy';

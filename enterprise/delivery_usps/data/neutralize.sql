-- disable usps
UPDATE delivery_carrier
SET usps_username = 'dummy';

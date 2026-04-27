-- disable easypost
UPDATE delivery_carrier
SET easypost_production_api_key = 'dummy';

-- neutralize Shopee API credentials
UPDATE shopee_account
   SET api_endpoint = 'test',
       partner_identifier = 1,
       partner_key = 'dummy';

UPDATE shopee_shop
   SET shop_identifier = 1,
       access_token = 'dummy',
       refresh_token = 'dummy';

-- disable amazon integration
UPDATE amazon_account
   SET seller_key = 'dummy',
       refresh_token = 'dummy';

-- disable the Paymob POS integration
UPDATE pos_payment_method
   SET paymob_api_key = 'dummy_value',
       paymob_hmac_secret = 'dummy_value'
   WHERE paymob_api_key IS NOT NULL;

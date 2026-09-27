-- disable PayU payment provider
UPDATE payment_provider
   SET payu_key_id = NULL,
       payu_merchant_salt = NULL;

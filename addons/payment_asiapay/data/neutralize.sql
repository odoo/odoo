-- disable asiapay payment provider
UPDATE payment_provider
   SET asiapay_merchant_id = NULL,
       asiapay_secure_hash_secret = NULL,
       asiapay_secure_hash_function = NULL;

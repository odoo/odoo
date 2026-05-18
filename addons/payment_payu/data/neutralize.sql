-- disable payu payment provider
UPDATE payment_provider
   SET payu_merchant_key = NULL,
       payu_merchant_salt = NULL;

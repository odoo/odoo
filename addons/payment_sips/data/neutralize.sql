-- disable sips payment provider
UPDATE payment_provider
   SET sips_merchant_id = NULL,
       sips_secret = NULL;

-- disable payumoney payment provider
UPDATE payment_provider
   SET payumoney_merchant_key = NULL,
       payumoney_merchant_salt = NULL;

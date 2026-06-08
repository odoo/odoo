-- disable adyen payment provider
UPDATE payment_provider
   SET adyen_merchant_account = NULL,
       adyen_api_key = NULL,
       adyen_hmac_key = NULL;

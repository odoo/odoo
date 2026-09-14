-- disable adyen payment provider
UPDATE payment_provider
   SET adyen_merchant_account = NULL;

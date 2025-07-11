-- disable redsys payment provider
UPDATE payment_provider
   SET redsys_merchant_code = NULL,
       redsys_merchant_terminal = NULL,
       redsys_secret_key = NULL;

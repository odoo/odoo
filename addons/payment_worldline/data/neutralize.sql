-- disable worldline payment provider
UPDATE payment_provider
   SET worldline_pspid = NULL,
       worldline_api_key = NULL,
       worldline_api_secret = NULL,
       worldline_webhook_key = NULL,
       worldline_webhook_secret = NULL;

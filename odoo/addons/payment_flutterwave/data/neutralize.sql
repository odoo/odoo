-- disable flutterwave payment provider
UPDATE payment_provider
   SET flutterwave_public_key = NULL,
       flutterwave_secret_key = NULL,
       flutterwave_webhook_secret = NULL;

-- disable flutterwave payment provider
UPDATE payment_provider
   SET flutterwave_public_key = NULL;

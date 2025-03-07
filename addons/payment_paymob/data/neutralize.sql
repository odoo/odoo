-- disable paymob payment provider
UPDATE payment_provider
   SET paymob_email_account = NULL,
       paymob_client_id = NULL,
       paymob_client_secret = NULL;

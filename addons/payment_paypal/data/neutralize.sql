-- disable paypal payment provider
UPDATE payment_provider
   SET paypal_email_account = NULL,
       paypal_client_id = NULL,
       paypal_client_secret = NULL;

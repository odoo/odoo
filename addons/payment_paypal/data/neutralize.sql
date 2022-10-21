-- disable paypal payment provider
UPDATE payment_provider
   SET paypal_email_account = NULL,
       paypal_pdt_token = NULL;

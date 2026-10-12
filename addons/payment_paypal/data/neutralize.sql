-- disable paypal payment provider
UPDATE payment_provider
   SET paypal_email_account = NULL,
       paypal_account_id = NULL,
       paypal_client_id = NULL,
       paypal_client_secret = NULL,
       paypal_seller_nonce = NULL,
       paypal_is_oauth_onboarded = NULL,
       paypal_payments_receivable = NULL,
       paypal_email_confirmed = NULL,
       paypal_access_token = NULL,
       paypal_access_token_expiry = NULL;

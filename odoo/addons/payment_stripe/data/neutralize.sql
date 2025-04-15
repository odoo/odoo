-- disable stripe payment provider
UPDATE payment_provider
   SET stripe_secret_key = NULL,
       stripe_publishable_key = NULL,
       stripe_webhook_secret = NULL;

-- disable stripe payment provider
UPDATE payment_provider
   SET stripe_publishable_key = NULL;

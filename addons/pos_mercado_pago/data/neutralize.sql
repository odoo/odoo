UPDATE pos_payment_provider
   SET mp_bearer_token = 'dummy_value',
       mp_webhook_secret_key = 'dummy_value'
   WHERE mp_bearer_token IS NOT NULL;

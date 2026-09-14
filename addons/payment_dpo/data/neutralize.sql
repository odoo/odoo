-- disable dpo payment provider
UPDATE payment_provider
   SET dpo_service_ref = NULL;

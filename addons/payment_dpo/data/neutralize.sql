-- disable dpo payment provider
UPDATE payment_provider
   SET dpo_company_token = NULL,
       dpo_service_ref = NULL;

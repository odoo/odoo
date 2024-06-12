-- disable payulatam payment provider
UPDATE payment_provider
   SET payulatam_merchant_id = NULL,
       payulatam_account_id = NULL,
       payulatam_api_key = NULL;

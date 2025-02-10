-- disable Gelato
UPDATE res_company
   SET gelato_api_key = NULL,
       gelato_webhook_secret = NULL;

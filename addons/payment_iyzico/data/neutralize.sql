-- disable Iyzico payment provider
UPDATE payment_provider
   SET iyzico_key_id = NULL;

-- disable mollie payment provider
UPDATE payment_provider
   SET mollie_api_key = NULL;

-- disable sslcommerz payment provider
UPDATE payment_provider
   SET sslcommerz_store_id = NULL,
       sslcommerz_store_passwd = NULL;

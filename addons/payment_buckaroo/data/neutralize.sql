-- disable buckaroo payment provider
UPDATE payment_provider
   SET buckaroo_website_key = NULL;

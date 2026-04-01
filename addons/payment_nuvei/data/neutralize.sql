-- disable nuvei payment provider
UPDATE payment_provider
   SET nuvei_merchant_identifier = NULL,
       nuvei_site_identifier = NULL,
       nuvei_secret_key = NULL;

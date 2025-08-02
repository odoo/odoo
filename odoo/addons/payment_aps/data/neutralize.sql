-- disable aps payment provider
UPDATE payment_provider
   SET aps_merchant_identifier = NULL,
       aps_access_code = NULL,
       aps_sha_request = NULL,
       aps_sha_response = NULL;

-- disable authorize payment provider
UPDATE payment_provider
   SET authorize_login = NULL,
       authorize_client_key = NULL;

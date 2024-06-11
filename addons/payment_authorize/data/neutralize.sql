-- disable authorize payment provider
UPDATE payment_provider
   SET authorize_login = NULL,
       authorize_transaction_key = NULL,
       authorize_signature_key = NULL,
       authorize_client_key = NULL;

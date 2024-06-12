-- disable ogone payment provider
UPDATE payment_provider
   SET ogone_pspid = NULL,
       ogone_userid = NULL,
       ogone_password = NULL,
       ogone_shakey_in = NULL,
       ogone_shakey_out = NULL;

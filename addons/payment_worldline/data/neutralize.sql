-- disable worldline payment provider
UPDATE payment_provider
   SET worldline_pspid = NULL;

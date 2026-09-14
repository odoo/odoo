-- disable paymob payment provider
UPDATE payment_provider
    SET paymob_public_key = NULL;

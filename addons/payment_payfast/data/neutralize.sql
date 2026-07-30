-- disable payfast payment provider
UPDATE payment_provider
    SET payfast_merchant_id = NULL,
        payfast_merchant_key = NULL,
        payfast_passphrase = NULL;

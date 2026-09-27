-- disable generic payment provider
UPDATE payment_provider
   SET is_live = False;

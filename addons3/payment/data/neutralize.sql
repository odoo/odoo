-- disable generic payment provider
UPDATE payment_provider
   SET state = 'disabled'
 WHERE state NOT IN ('test', 'disabled');

-- disable generic payment provider
UPDATE payment_provider
   SET state = 'disabled'
 WHERE state NOT IN ('test', 'disabled');

-- the providers' secrets are encrypted and cannot be blanked column by column
UPDATE payment_provider
   SET provider_credential_id = NULL
 WHERE provider_credential_id IS NOT NULL;

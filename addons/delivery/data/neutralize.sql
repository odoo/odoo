-- disable prod environment in all delivery carriers
UPDATE delivery_carrier
   SET prod_environment = false;
-- disable delivery carriers from external providers
UPDATE delivery_carrier
   SET active = false
   WHERE delivery_type NOT IN ('fixed', 'base_on_rule');
-- carrier secrets are encrypted and cannot be blanked column by column
UPDATE delivery_carrier
   SET carrier_credential_id = NULL
 WHERE carrier_credential_id IS NOT NULL;

-- disable prod environment in all delivery methods
UPDATE delivery_carrier
   SET prod_environment = false;
-- disable delivery methods from external providers
UPDATE delivery_carrier
   SET active = false
   WHERE delivery_type NOT IN ('fixed', 'base_on_rule');

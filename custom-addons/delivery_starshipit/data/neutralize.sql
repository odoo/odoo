-- disable starshipit
UPDATE delivery_carrier
   SET starshipit_api_key = 'dummy',
       starshipit_subscription_key = 'dummy'
 WHERE delivery_type = 'starshipit';

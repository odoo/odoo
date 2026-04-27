-- disable envia
UPDATE delivery_carrier
   SET envia_production_api_key = 'dummy',
       envia_sandbox_api_key = 'dummy'
 WHERE delivery_type = 'envia';


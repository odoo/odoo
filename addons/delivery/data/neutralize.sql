-- disable delivery carriers
UPDATE delivery_carrier
   SET prod_environment = false,
       active = false;

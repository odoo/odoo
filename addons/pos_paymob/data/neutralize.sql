-- force the Paymob POS integration into the staging environment
UPDATE pos_payment_method
   SET paymob_test_mode = true;

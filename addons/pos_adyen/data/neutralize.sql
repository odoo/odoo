-- disable Adyen Payement POS integration
UPDATE pos_payment_method
   SET adyen_test_mode = true;

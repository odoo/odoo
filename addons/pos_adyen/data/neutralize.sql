-- disable Adyen Payement POS integration
UPDATE pos_payment_method
   SET test_mode = true;

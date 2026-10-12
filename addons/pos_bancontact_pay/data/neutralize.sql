-- disable Bancontact Payment POS integration
UPDATE pos_payment_method
   SET bancontact_test_mode = true;

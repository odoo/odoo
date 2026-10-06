-- disable Bancontact Payment POS integration
UPDATE pos_bancontact_product
   SET preprod = true;

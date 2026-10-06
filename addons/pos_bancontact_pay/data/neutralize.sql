-- disable Bancontact Payment POS integration
UPDATE pos_bancontact_product
   SET preprod = true;

-- remove the Bancontact Pay signing keys
UPDATE res_company
   SET bancontact_signing_key = NULL,
       bancontact_signing_kid = NULL;

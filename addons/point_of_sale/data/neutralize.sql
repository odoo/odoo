-- the payment terminals' secrets are encrypted and cannot be blanked column by column
UPDATE pos_payment_method
   SET terminal_credential_id = NULL
 WHERE terminal_credential_id IS NOT NULL;

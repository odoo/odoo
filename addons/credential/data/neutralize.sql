-- company secrets are encrypted and cannot be blanked column by column
UPDATE res_company
   SET company_credential_id = NULL
 WHERE company_credential_id IS NOT NULL;

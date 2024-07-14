-- disable account_taxcloud integration
UPDATE res_company
   SET taxcloud_api_id = NULL,
       taxcloud_api_key = NULL;

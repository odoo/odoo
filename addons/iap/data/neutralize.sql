UPDATE iap_account SET account_token = REGEXP_REPLACE(account_token, '(\+.*)?$', '+disabled');

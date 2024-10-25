-- happy path
UPDATE iap_account
SET account_token = REGEXP_REPLACE(account_token, '(\+.*)?$', '+disabled')
WHERE LENGTH(account_token) <= 33;
-- Legacy (invalid) records (pre v17)
UPDATE iap_account
SET account_token = 'dummy_value+disabled'
WHERE LENGTH(account_token) > 33
    AND account_token NOT LIKE '%+disabled';
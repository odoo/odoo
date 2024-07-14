-- delete LinkedIn Access Tokens
UPDATE social_account
   SET linkedin_account_urn = NULL,
       linkedin_access_token = NULL;
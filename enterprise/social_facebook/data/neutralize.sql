-- delete Facebook Access Tokens
UPDATE social_account
   SET facebook_account_id = NULL,
       facebook_access_token = NULL;
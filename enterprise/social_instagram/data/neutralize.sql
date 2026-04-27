-- delete Instagram Access Tokens
UPDATE social_account
   SET instagram_account_id = NULL,
       instagram_facebook_account_id = NULL,
       instagram_access_token = NULL;
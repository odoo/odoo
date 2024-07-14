-- delete Twitter Access Tokens
UPDATE social_account
   SET twitter_user_id = NULL,
       twitter_oauth_token = NULL,
       twitter_oauth_token_secret = NULL;
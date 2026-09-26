-- disable oauth providers
UPDATE auth_oauth_provider
   SET enabled = false;

-- remove oauth client secrets
UPDATE auth_oauth_provider
   SET client_secret = NULL;

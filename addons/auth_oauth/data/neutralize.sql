-- disable oauth providers
UPDATE auth_oauth_provider
   SET enabled = false;

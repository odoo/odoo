-- delete Youtube Access Tokens
UPDATE social_account
   SET youtube_channel_id = NULL,
       youtube_access_token = NULL,
       youtube_refresh_token = NULL,
       youtube_token_expiration_date = NULL,
       youtube_upload_playlist_id = NULL;
-- delete domains on websites
UPDATE website
   SET domain = NULL;

-- activate neutralization watermarks
UPDATE ir_ui_view
   SET active = true
 WHERE key = 'website.neutralize_ribbon';

-- disable cdn
UPDATE website
   SET cdn_activated = false;

-- Update robots.txt to disallow all crawling
UPDATE website
   SET robots_txt = E'User-agent: *\nDisallow: /';

-- website secrets are encrypted and cannot be blanked column by column
UPDATE website
   SET website_credential_id = NULL,
       plausible_shared_key_set = false
 WHERE website_credential_id IS NOT NULL;

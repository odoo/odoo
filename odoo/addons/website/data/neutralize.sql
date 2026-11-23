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

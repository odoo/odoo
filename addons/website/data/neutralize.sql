-- delete domains on websites
UPDATE website
   SET domain = NULL;

-- activate neutralization watermarks
UPDATE ir_ui_view
   SET active = true
 WHERE key = 'website.neutralize_ribbon';

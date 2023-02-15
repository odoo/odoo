-- activate neutralization watermarks
UPDATE ir_ui_view
   SET active = true
 WHERE key = 'web.neutralize_banner';

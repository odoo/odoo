-- deactivate mail template
UPDATE mail_template
   SET mail_server_id = NULL;
-- deactivate fetchmail server
UPDATE fetchmail_server
   SET active = false;

-- reset WEB Push Notification:
-- * delete VAPID/JWT keys
DELETE FROM ir_config_parameter
    WHERE key IN ('mail.web_push_vapid_private_key', 'mail.web_push_vapid_public_key', 'mail.sfu_server_key');
-- * delete delayed messages (CRON)
TRUNCATE mail_notification_web_push;
-- * delete Devices for each partners
TRUNCATE mail_partner_device CASCADE;

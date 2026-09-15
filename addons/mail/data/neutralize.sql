-- deactivate mail servers
UPDATE ir_mail_server
   SET active = false;

-- insert dummy mail server to prevent using fallback servers specified using command line
INSERT INTO ir_mail_server(name, smtp_port, smtp_host, smtp_encryption, active, smtp_authentication)
VALUES ('neutralization - disable emails', 1025, 'invalid', 'none', true, 'login');

-- deactivate mail template
UPDATE mail_template
   SET mail_server_id = NULL;
-- deactivate fetchmail server
UPDATE fetchmail_server
   SET active = false;

-- reset WEB Push Notification:
-- * delete VAPID/JWT keys
DELETE FROM ir_config_parameter
    WHERE key = 'mail.web_push_vapid_public_key';
-- disconnect third-party services: RTC (SFU, Twilio), translation, GIF
-- (a boolean config parameter is unset when its row is absent)
DELETE FROM ir_config_parameter
    WHERE key IN ('mail.use_sfu_server', 'mail.sfu_server_url',
                  'mail.use_twilio_rtc_servers', 'mail.twilio_account_sid');
DELETE FROM credential_credential
    WHERE company_id IS NULL
      AND name IN ('System secret: mail.sfu_server_key', 'System secret: mail.twilio_account_token',
                   'System secret: mail.google_translate_api_key', 'System secret: discuss.klipy_api_key',
                   'System secret: mail.web_push_vapid_private_key',
                   'System secret: mail.sfu_local_key');
-- incoming mail and TURN secrets are encrypted and cannot be blanked column by column
UPDATE fetchmail_server
   SET server_credential_id = NULL
 WHERE server_credential_id IS NOT NULL;
UPDATE mail_ice_server
   SET ice_credential_id = NULL
 WHERE ice_credential_id IS NOT NULL;
-- * delete delayed messages (CRON)
TRUNCATE mail_push;
-- * delete Devices for each partners
DELETE FROM mail_push_device;

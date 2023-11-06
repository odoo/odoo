-- deactivate mail template
UPDATE mail_template
   SET mail_server_id = NULL;
-- deactivate fetchmail server
UPDATE fetchmail_server
   SET active = false;

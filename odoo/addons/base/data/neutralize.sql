-- deactivate mail servers and drop their credentials: a neutralized database
-- is meant to be copied around, and an archived server still ships a working
-- password in every dump
UPDATE ir_mail_server
   SET active = false,
       smtp_user = NULL,
       smtp_pass = NULL;

-- insert dummy mail server to prevent using fallback servers specified using command line
INSERT INTO ir_mail_server(name, smtp_port, smtp_host, smtp_encryption, active, smtp_authentication)
VALUES ('neutralization - disable emails', 1025, 'invalid', 'none', true, 'login');

-- deactivate crons
UPDATE ir_cron
   SET active = false
 WHERE id NOT IN (
       SELECT res_id
         FROM ir_model_data
        WHERE model = 'ir.cron'
          AND name = 'autovacuum_job'
          AND module = 'base'
);

-- neutralization flag for the database
INSERT INTO ir_config_parameter (key, value)
VALUES ('database.is_neutralized', 'True')
    ON CONFLICT (key) DO
       UPDATE SET value = 'True';

-- deactivate webhooks
UPDATE ir_act_server
   SET webhook_url = 'neutralization - disable webhook'
 WHERE state = 'webhook';

-- prevent access to database.secret protected data
UPDATE ir_config_parameter
   SET value = 'dummysecret'
 WHERE key = 'database.secret';

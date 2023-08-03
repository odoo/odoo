-- deactivate mail servers
UPDATE ir_mail_server
   SET active = false;

INSERT INTO ir_mail_server (name, smtp_port, smtp_host, smtp_encryption, active, smtp_authentication)
VALUES ('neutralize emails', 1025, 'smtp.example.org', 'none', true, 'login');

-- deactivate crons
UPDATE ir_cron
   SET active = false
 WHERE id NOT IN (
       SELECT res_id
         FROM ir_model_data
        WHERE model = 'ir.cron'
          AND name = 'autovacuum_job'
);

-- neutralization flag for the database
INSERT INTO ir_config_parameter (key, value)
VALUES ('database.is_neutralized', true)
    ON CONFLICT (key) DO
       UPDATE SET value = true;

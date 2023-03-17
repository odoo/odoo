-- deactivate mail servers
UPDATE ir_mail_server
   SET active = false,
       smtp_user = COALESCE(smtp_user || '_neutralised', 'remove_this_to_enable_this_mail_server');

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

def migrate(cr, version):
    # Four scheduled actions read "Remote Remote:" in the UI, a doubled module
    # word left by a rename sweep. Their data files are noupdate="1", so the
    # corrected names never reach a database that already has the records. The
    # name lives on the delegated ir.actions.server, and cron_name caches it.
    cr.execute(
        """
        UPDATE ir_act_server s
           SET name = jsonb_build_object(
                   'en_US',
                   replace(s.name->>'en_US', 'Remote Remote: ', 'Remote: ')
               ) || (s.name - 'en_US')
          FROM ir_cron c, ir_model_data d
         WHERE c.ir_actions_server_id = s.id
           AND d.module = 'device'
           AND d.model = 'ir.cron'
           AND d.res_id = c.id
           AND s.name->>'en_US' LIKE 'Remote Remote: %'
        """
    )
    cr.execute(
        """
        UPDATE ir_cron c
           SET cron_name = replace(c.cron_name, 'Remote Remote: ', 'Remote: ')
          FROM ir_model_data d
         WHERE d.module = 'device'
           AND d.model = 'ir.cron'
           AND d.res_id = c.id
           AND c.cron_name LIKE 'Remote Remote: %'
        """
    )

def migrate(cr, version):
    cr.execute("SELECT to_regclass('public.sifnext_legacy_unit_department_map')")
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'sifnext_ppl' AND name = 'unit_uat_ppl'
         LIMIT 1
        """
    )
    legacy_xmlid = cr.fetchone()
    if not legacy_xmlid:
        return

    cr.execute(
        "SELECT department_id FROM sifnext_legacy_unit_department_map WHERE unit_id = %s",
        (legacy_xmlid[0],),
    )
    mapping = cr.fetchone()
    if mapping:
        cr.execute(
            """
            UPDATE ir_model_data
               SET name = 'department_uat_ppl', model = 'hr.department', res_id = %s
             WHERE module = 'sifnext_ppl' AND name = 'unit_uat_ppl'
            """,
            (mapping[0],),
        )

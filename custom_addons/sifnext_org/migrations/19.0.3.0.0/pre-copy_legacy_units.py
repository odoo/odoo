def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return bool(cr.fetchone()[0])


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = %s
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if _table_exists(cr, "sifnext_unit"):
        cr.execute(
            """
            CREATE TABLE IF NOT EXISTS sifnext_legacy_unit_backup (
                unit_id integer PRIMARY KEY,
                name text NOT NULL,
                code text NOT NULL,
                active boolean,
                company_id integer,
                journal_unit_dept text
            )
            """
        )
        cr.execute(
            """
            INSERT INTO sifnext_legacy_unit_backup
                (unit_id, name, code, active, company_id, journal_unit_dept)
            SELECT id, name, code, active, company_id, journal_unit_dept
              FROM sifnext_unit
            ON CONFLICT (unit_id) DO UPDATE SET
                name = EXCLUDED.name,
                code = EXCLUDED.code,
                active = EXCLUDED.active,
                company_id = EXCLUDED.company_id,
                journal_unit_dept = EXCLUDED.journal_unit_dept
            """
        )

    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS sifnext_legacy_unit_rel_backup (
            model_name text NOT NULL,
            record_id integer NOT NULL,
            unit_id integer NOT NULL,
            PRIMARY KEY (model_name, record_id)
        )
        """
    )
    for table_name, model_name in (
        ("res_users", "res.users"),
        ("sifnext_ppl", "sifnext.ppl"),
        ("transaksi_transaction", "transaksi.transaction"),
    ):
        if not _table_exists(cr, table_name) or not _column_exists(cr, table_name, "unit_id"):
            continue
        cr.execute(
            """
            INSERT INTO sifnext_legacy_unit_rel_backup (model_name, record_id, unit_id)
            SELECT %s, id, unit_id
              FROM %s
             WHERE unit_id IS NOT NULL
            ON CONFLICT (model_name, record_id) DO UPDATE SET unit_id = EXCLUDED.unit_id
            """ % ("%s", table_name),
            (model_name,),
        )

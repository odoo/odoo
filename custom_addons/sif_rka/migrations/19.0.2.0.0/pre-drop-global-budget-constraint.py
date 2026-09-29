def migrate(cr, version):
    cr.execute("SELECT to_regclass('public.sif_rka_budget')")
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT conname
          FROM pg_constraint
         WHERE conrelid = 'sif_rka_budget'::regclass
           AND contype = 'u'
           AND pg_get_constraintdef(oid) = 'UNIQUE (account_id, tahun)'
        """
    )
    for (constraint_name,) in cr.fetchall():
        escaped = constraint_name.replace('"', '""')
        cr.execute('ALTER TABLE sif_rka_budget DROP CONSTRAINT "%s"' % escaped)

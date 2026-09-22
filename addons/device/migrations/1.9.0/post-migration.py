def migrate(cr, version):
    # device_id lost index=True: _device_timestamp_idx leads with the same
    # column, so the standalone btree answered nothing it does not while costing
    # every insert into the family's append-heavy table. Odoo drops an index it
    # manages when the flag goes, but the name it used is not guaranteed to be
    # the one on an older database, so the leftovers are named here too.
    cr.execute(
        """
        SELECT indexname, tablename
          FROM pg_indexes
         WHERE indexname LIKE '%\\_\\_device\\_id\\_index'
           AND tablename IN (
                SELECT DISTINCT c.relname
                  FROM pg_index i
                  JOIN pg_class c ON c.oid = i.indrelid
                  JOIN pg_class ic ON ic.oid = i.indexrelid
                 WHERE ic.relname LIKE '%\\_device\\_timestamp\\_idx'
           )
        """
    )
    for indexname, tablename in cr.fetchall():
        cr.execute(f'DROP INDEX IF EXISTS "{indexname}"')
        cr.execute(
            "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s",
            (tablename, f"{tablename}_device_timestamp_idx"),
        )
        assert cr.fetchone(), (
            f"{tablename} lost its device_id index and has no composite to "
            "answer device lookups with"
        )

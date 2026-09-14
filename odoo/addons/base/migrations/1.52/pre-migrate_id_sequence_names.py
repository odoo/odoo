from odoo.tools import SQL

MAX_IDENTIFIER_LENGTH = 63


def _misnamed_id_sequences(cr):
    cr.execute(
        """
        SELECT sequence.relname, owner.relname
          FROM pg_class sequence
          JOIN pg_depend dependency
            ON dependency.objid = sequence.oid
           AND dependency.classid = 'pg_class'::regclass
           AND dependency.deptype = 'a'
          JOIN pg_class owner ON owner.oid = dependency.refobjid
          JOIN pg_attribute attribute
            ON attribute.attrelid = owner.oid AND attribute.attnum = dependency.refobjsubid
         WHERE sequence.relkind = 'S'
           AND sequence.relnamespace = current_schema::regnamespace
           AND attribute.attname = 'id'
           AND sequence.relname <> owner.relname || '_id_seq'
           AND length(owner.relname || '_id_seq') <= %s
           AND NOT EXISTS (
               SELECT 1 FROM pg_class taken
                WHERE taken.relname = owner.relname || '_id_seq'
                  AND taken.relnamespace = current_schema::regnamespace
           )
         ORDER BY owner.relname
        """,
        [MAX_IDENTIFIER_LENGTH],
    )
    return cr.fetchall()


def migrate(cr, version):
    for sequence, table in _misnamed_id_sequences(cr):
        cr.execute(
            SQL(
                "ALTER SEQUENCE %s RENAME TO %s",
                SQL.identifier(sequence),
                SQL.identifier(table + "_id_seq"),
            )
        )

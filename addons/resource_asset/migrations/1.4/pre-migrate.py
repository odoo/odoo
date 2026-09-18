import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """`resource.asset` is a table-inheritance root now, and PostgreSQL does not
    check a foreign key against a row in an inheriting child table: once a
    subtype exists, every one of these would refuse a perfectly good reference.

    `Registry.check_foreign_keys` only adds and replaces what the registry
    declares, so a constraint it has stopped declaring stays until something
    drops it. `mixin.table.inheritance.root` enforces the same `ondelete` rules
    in Python from here on.
    """
    if not version:
        return
    cr.execute(
        SQL(
            """
            SELECT c.conrelid::regclass::text, c.conname
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.confrelid
             WHERE c.contype = 'f' AND t.relname = 'resource_asset'
             ORDER BY 1, 2
            """
        )
    )
    constraints = cr.fetchall()
    for table, name in constraints:
        cr.execute(
            SQL(
                "ALTER TABLE %s DROP CONSTRAINT %s",
                SQL.identifier(table),
                SQL.identifier(name),
            )
        )
    _logger.info(
        "resource_asset: dropped %d foreign key(s) pointing at a table-inheritance "
        "root; their ondelete is enforced in Python now.",
        len(constraints),
    )

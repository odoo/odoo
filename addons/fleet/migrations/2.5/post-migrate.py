import logging

from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

COLUMNS = ("license_plate", "vin_sn", "engine_sn")


def _tables_of_tree(cr):
    cr.execute(
        """
        SELECT child.relname
          FROM pg_inherits
          JOIN pg_class child ON child.oid = pg_inherits.inhrelid
          JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
         WHERE parent.relname = 'resource_asset'
        """
    )
    return ["resource_asset", *(row[0] for row in cr.fetchall())]


def _views_reading(cr, table, column):
    cr.execute(
        """
        SELECT DISTINCT dependee.relname
          FROM pg_depend d
          JOIN pg_rewrite r ON r.oid = d.objid
          JOIN pg_class dependee ON dependee.oid = r.ev_class
          JOIN pg_class ref ON ref.oid = d.refobjid
          JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
         WHERE ref.relname = %s AND a.attname = %s AND dependee.relkind IN ('v', 'm')
        """,
        [table, column],
    )
    return [row[0] for row in cr.fetchall()]


def migrate(cr, version):
    if not table_exists(cr, "resource_asset_vehicle"):
        return
    for column in COLUMNS:
        legacy = f"legacy_{column}"
        if column_exists(cr, "resource_asset_vehicle", legacy):
            cr.execute(
                SQL(
                    "UPDATE resource_asset_vehicle SET %s = %s WHERE %s IS NULL AND %s IS NOT NULL",
                    SQL.identifier(column),
                    SQL.identifier(legacy),
                    SQL.identifier(column),
                    SQL.identifier(legacy),
                )
            )
        # A member table created with its columns spelled out keeps a copy of
        # an inherited column after the root drops it, so every table drops.
        # A SQL view reading the column goes with it; its module recreates it
        # from the new column when that module is updated.
        for table in _tables_of_tree(cr):
            if not column_exists(cr, table, legacy):
                continue
            views = _views_reading(cr, table, legacy)
            if views:
                _logger.warning(
                    "fleet 2.5: dropping %s.%s takes the SQL view(s) %s with it; "
                    "update the module that owns each to recreate it.",
                    table,
                    legacy,
                    ", ".join(views),
                )
            cr.execute(
                SQL(
                    "ALTER TABLE %s DROP COLUMN %s CASCADE",
                    SQL.identifier(table),
                    SQL.identifier(legacy),
                )
            )

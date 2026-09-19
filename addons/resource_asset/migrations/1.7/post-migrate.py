from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

from odoo.addons.resource_asset.table_inheritance import move_rows_into_subtype_table

SUBTYPES = {
    "property": ("cadastral_id",),
    "telecom": ("imei",),
    "device": ("imei",),
}


def migrate(cr, version):
    for code, columns in SUBTYPES.items():
        table = f"resource_asset_{code}"
        if not table_exists(cr, table):
            continue
        move_rows_into_subtype_table(cr, code, table)
        for column in columns:
            legacy = f"legacy_{column}"
            # A stored compute the subtype declares is computed from the
            # identifier rows when its column is new, so the copy is a
            # shortcut, never a requirement.
            if column_exists(cr, "resource_asset", legacy) and column_exists(
                cr, table, column
            ):
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE %s IS NULL AND %s IS NOT NULL",
                        SQL.identifier(table),
                        SQL.identifier(column),
                        SQL.identifier(legacy),
                        SQL.identifier(column),
                        SQL.identifier(legacy),
                    )
                )
    for column in {c for columns in SUBTYPES.values() for c in columns}:
        legacy = f"legacy_{column}"
        if column_exists(cr, "resource_asset", legacy):
            cr.execute(
                SQL(
                    "ALTER TABLE resource_asset DROP COLUMN %s",
                    SQL.identifier(legacy),
                )
            )

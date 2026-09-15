from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

from odoo.addons.account_depreciation.tools.legacy_assets import LEGACY_TABLE

RENAMED_TABLES = {
    "account_asset": LEGACY_TABLE,
    "asset_move_line_rel": "legacy_asset_move_line_rel",
}


def migrate(cr, version):
    if not version or not table_exists(cr, "account_asset"):
        return
    if table_exists(cr, "asset_modify"):
        cr.execute("DELETE FROM asset_modify")
    for old, new in RENAMED_TABLES.items():
        if table_exists(cr, old) and not table_exists(cr, new):
            cr.execute(
                SQL(
                    "ALTER TABLE %s RENAME TO %s",
                    SQL.identifier(old),
                    SQL.identifier(new),
                )
            )
    if column_exists(cr, "account_move", "depreciation_asset_id"):
        cr.execute(
            """
            SELECT conname FROM pg_constraint
             WHERE conrelid = 'account_move'::regclass AND contype = 'f'
               AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                                    WHERE attrelid = 'account_move'::regclass
                                      AND attname = 'depreciation_asset_id')]
            """
        )
        for (name,) in cr.fetchall():
            cr.execute(
                SQL("ALTER TABLE account_move DROP CONSTRAINT %s", SQL.identifier(name))
            )
        cr.execute(
            "ALTER TABLE account_move RENAME COLUMN depreciation_asset_id TO legacy_depreciation_asset_id"
        )
        cr.execute(
            "ALTER INDEX IF EXISTS account_move__depreciation_asset_id_index RENAME TO account_move__legacy_depreciation_asset_id_index"
        )

import logging

from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

from odoo.addons.account_depreciation.tools.legacy_assets import LEGACY_TABLE, MAP_TABLE

_logger = logging.getLogger(__name__)

# The board's own columns, as they were on resource_asset. Delegated columns
# (name, company, value_original, the dates) stay on the asset.
BOARD_COLUMNS = (
    "depreciation_state",
    "depreciation_method",
    "depreciation_duration",
    "depreciation_period",
    "depreciation_factor",
    "depreciation_prorata",
    "date_prorata",
    "account_asset_id",
    "asset_group_id",
    "account_depreciation_id",
    "account_depreciation_expense_id",
    "depreciation_journal_id",
    "value_book",
    "value_salvage",
    "value_non_deductible_tax",
    "depreciation_profile_id",
    "value_depreciated_import",
    "depreciation_paused_days",
    "value_gain_on_sale",
)
DROPPED_COLUMNS = (*BOARD_COLUMNS, "increased_asset_id")


def migrate(cr, version):
    """The depreciation board is a record of its own, one per depreciating asset.

    Two sources: a database that ran 1.4 earlier carries the board on the
    asset's columns; one upgrading from account.asset in this same run has
    1.4's legacy table and map still in place (its end-migrate drops them),
    and 1.4 could not land columns the asset no longer has."""
    if not version:
        return
    if column_exists(cr, "resource_asset", "depreciation_state"):
        created = _boards_from_asset_columns(cr)
    elif table_exists(cr, LEGACY_TABLE) and table_exists(cr, MAP_TABLE):
        created = _boards_from_legacy(cr)
    else:
        return
    cr.execute(
        """
        UPDATE account_move m
           SET depreciation_board_id = b.id
          FROM account_depreciation_board b
         WHERE b.asset_id = m.depreciation_asset_id AND m.depreciation_board_id IS NULL
        """
    )
    if table_exists(cr, "asset_move_line_rel"):
        cr.execute(
            """
            INSERT INTO depreciation_board_move_line_rel (board_id, line_id)
            SELECT b.id, rel.line_id
              FROM asset_move_line_rel rel
              JOIN account_depreciation_board b ON b.asset_id = rel.asset_id
            ON CONFLICT DO NOTHING
            """
        )
    _logger.info("account_depreciation 1.5: %d board(s) created", created)
    for column in DROPPED_COLUMNS:
        cr.execute(
            SQL(
                "ALTER TABLE resource_asset DROP COLUMN IF EXISTS %s CASCADE",
                SQL.identifier(column),
            )
        )
    cr.execute("DROP TABLE IF EXISTS asset_move_line_rel")


def _boards_from_asset_columns(cr):
    columns = SQL(", ").join(SQL.identifier(name) for name in BOARD_COLUMNS)
    cr.execute(
        SQL(
            """
            INSERT INTO account_depreciation_board (asset_id, %(columns)s, create_uid, create_date, write_uid, write_date)
            SELECT id, %(columns)s, create_uid, create_date, write_uid, write_date
              FROM resource_asset
             WHERE depreciation_state IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM account_depreciation_board b WHERE b.asset_id = resource_asset.id)
            """,
            columns=columns,
        )
    )
    created = cr.rowcount
    cr.execute(
        """
        UPDATE account_depreciation_board b
           SET increased_board_id = parent.id
          FROM resource_asset a
          JOIN account_depreciation_board parent ON parent.asset_id = a.increased_asset_id
         WHERE b.asset_id = a.id AND a.increased_asset_id IS NOT NULL
        """
    )
    return created


def _boards_from_legacy(cr):
    present = [name for name in BOARD_COLUMNS if column_exists(cr, LEGACY_TABLE, name)]
    columns = SQL(", ").join(SQL.identifier(name) for name in present)
    legacy_columns = SQL(", ").join(
        SQL("legacy.%s", SQL.identifier(name)) for name in present
    )
    cr.execute(
        SQL(
            """
            INSERT INTO account_depreciation_board (asset_id, %(columns)s, create_uid, create_date, write_uid, write_date)
            SELECT map.resource_asset_id, %(legacy_columns)s, legacy.create_uid, legacy.create_date, legacy.write_uid, legacy.write_date
              FROM %(legacy)s legacy
              JOIN %(map)s map ON map.account_asset_id = legacy.id
             WHERE legacy.depreciation_state IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM account_depreciation_board b WHERE b.asset_id = map.resource_asset_id)
            """,
            columns=columns,
            legacy_columns=legacy_columns,
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )
    created = cr.rowcount
    cr.execute(
        SQL(
            """
            UPDATE account_depreciation_board b
               SET increased_board_id = parent.id
              FROM %(legacy)s legacy
              JOIN %(map)s map ON map.account_asset_id = legacy.id
              JOIN %(map)s parent_map ON parent_map.account_asset_id = legacy.parent_id
              JOIN account_depreciation_board parent ON parent.asset_id = parent_map.resource_asset_id
             WHERE b.asset_id = map.resource_asset_id
            """,
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )
    return created

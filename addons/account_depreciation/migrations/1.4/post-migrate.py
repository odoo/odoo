import csv
import logging
import os

import psycopg.types.json

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

from odoo.addons.account_depreciation.tools.legacy_assets import LEGACY_TABLE, MAP_TABLE

_logger = logging.getLogger(__name__)

MAPPING_ENV = "ODOO_ACCOUNT_ASSET_MAPPING"
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
    "analytic_distribution",
    "date_acquisition",
    "date_disposal",
    "value_original",
    "asset_properties",
)
GENERIC_REFERENCES = (
    ("mail_message", "model"),
    ("mail_followers", "res_model"),
    ("mail_activity", "res_model"),
    ("ir_attachment", "res_model"),
    ("ir_model_data", "model"),
    ("rating_rating", "res_model"),
)


class MappingRequiredError(Exception):
    pass


def migrate(cr, version):
    if not version or not table_exists(cr, LEGACY_TABLE):
        return
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
    cr.execute(
        SQL(
            "SELECT id FROM %s ORDER BY parent_id NULLS FIRST, id",
            SQL.identifier(LEGACY_TABLE),
        )
    )
    board_ids = [row[0] for row in cr.fetchall()]
    cr.execute(
        SQL(
            "CREATE TABLE IF NOT EXISTS %s (account_asset_id int PRIMARY KEY, resource_asset_id int NOT NULL, created boolean NOT NULL)",
            SQL.identifier(MAP_TABLE),
        )
    )
    if not board_ids:
        return
    targets = _read_targets(env, board_ids)
    _place_boards(env, board_ids, targets)
    _copy_board_columns(cr)
    _repoint_entries(cr)
    _repoint_references(env)
    _merge_definitions_onto_kinds(env)
    env.invalidate_all()
    cr.execute(
        SQL(
            "SELECT count(*) FILTER (WHERE created), count(*) FROM %s",
            SQL.identifier(MAP_TABLE),
        )
    )
    created, total = cr.fetchone()
    _logger.info(
        "account_depreciation: %d board(s) became resource assets, %d merged onto an existing asset and %d created",
        total,
        total - created,
        created,
    )


def _read_targets(env, board_ids):
    cr = env.cr
    targets = {}
    if column_exists(cr, LEGACY_TABLE, "asset_id"):
        cr.execute(
            SQL(
                "SELECT id, asset_id FROM %s WHERE asset_id IS NOT NULL",
                SQL.identifier(LEGACY_TABLE),
            )
        )
        targets.update(dict(cr.fetchall()))
    path = os.environ.get(MAPPING_ENV)
    if path and path != "none":
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("resource_asset_id", "").strip():
                    targets[int(row["account_asset_id"])] = int(
                        row["resource_asset_id"]
                    )
    cr.execute("SELECT count(*) FROM resource_asset")
    existing_assets = cr.fetchone()[0]
    unmapped = [board_id for board_id in board_ids if board_id not in targets]
    if existing_assets and unmapped and not path:
        raise MappingRequiredError(
            f"{len(unmapped)} depreciation board(s) name no asset, and the database "
            f"already holds {existing_assets} asset(s) they may describe. Set "
            f"{MAPPING_ENV} to a CSV of account_asset_id,resource_asset_id (an empty "
            f"resource_asset_id creates a new asset), or to 'none' to create a new "
            f"asset for every unmapped board, then upgrade again."
        )
    valid = set(env["resource.asset"].browse(set(targets.values())).exists().ids)
    missing = {board: asset for board, asset in targets.items() if asset not in valid}
    if missing:
        raise MappingRequiredError(
            f"The mapping names assets that do not exist: {sorted(missing.items())[:10]}"
        )
    return targets


def _place_boards(env, board_ids, targets):
    cr = env.cr
    columns = [
        "id",
        "name",
        "company_id",
        "active",
        "parent_id",
        "depreciation_profile_id",
        "create_uid",
        "create_date",
    ]
    cr.execute(
        SQL(
            "SELECT %s FROM %s WHERE id = ANY(%s)",
            SQL(", ").join(SQL.identifier(column) for column in columns),
            SQL.identifier(LEGACY_TABLE),
            board_ids,
        )
    )
    boards = {row[0]: dict(zip(columns, row, strict=True)) for row in cr.fetchall()}
    profile_kinds = {
        profile.id: profile.kind_id.id
        for profile in env["account.depreciation.profile"]
        .with_context(active_test=False)
        .search([])
    }
    fallback_kind = env.ref("account_depreciation.kind_fixed_asset").id
    Asset = env["resource.asset"].with_context(
        mail_create_nolog=True, tracking_disable=True, active_test=False
    )
    asset_map = {}
    taken = set()
    for board_id in board_ids:
        board = boards[board_id]
        target = targets.get(board_id)
        parent = asset_map.get(board["parent_id"]) if board["parent_id"] else False
        if target and target not in taken:
            asset_map[board_id] = target
            taken.add(target)
            cr.execute(
                SQL(
                    "INSERT INTO %s VALUES (%s, %s, false)",
                    SQL.identifier(MAP_TABLE),
                    board_id,
                    target,
                )
            )
            continue
        component_of = target or parent
        kind = profile_kinds.get(board["depreciation_profile_id"]) or fallback_kind
        asset = Asset.create(
            {
                "name": _name(board["name"]),
                "company_id": board["company_id"],
                "kind_id": kind,
                "parent_id": component_of,
            }
        )
        asset_map[board_id] = asset.id
        cr.execute(
            SQL(
                "UPDATE resource_asset SET active = %s, create_uid = %s, create_date = %s WHERE id = %s",
                board["active"],
                board["create_uid"],
                board["create_date"],
                asset.id,
            )
        )
        cr.execute(
            SQL(
                "UPDATE resource_resource SET active = %s WHERE id = %s",
                board["active"],
                asset.resource_id.id,
            )
        )
        cr.execute(
            SQL(
                "INSERT INTO %s VALUES (%s, %s, true)",
                SQL.identifier(MAP_TABLE),
                board_id,
                asset.id,
            )
        )
        # Since 1.5 the increase link is the board's, read from the legacy
        # parent through the map; before, it sits on the asset.
        if board["parent_id"] and column_exists(
            cr, "resource_asset", "increased_asset_id"
        ):
            cr.execute(
                SQL(
                    "UPDATE resource_asset SET increased_asset_id = %s WHERE id = %s",
                    parent,
                    asset.id,
                )
            )
    env["resource.asset"].flush_model()


def _name(value):
    if isinstance(value, dict):
        return value.get("en_US") or next(iter(value.values()), "")
    return value or ""


def _copy_board_columns(cr):
    present = [
        column
        for column in BOARD_COLUMNS
        if column_exists(cr, LEGACY_TABLE, column)
        and column_exists(cr, "resource_asset", column)
    ]
    cr.execute(
        SQL(
            """
            UPDATE resource_asset asset
               SET %(assignments)s
              FROM %(legacy)s legacy
              JOIN %(map)s map ON map.account_asset_id = legacy.id
             WHERE asset.id = map.resource_asset_id
            """,
            assignments=SQL(", ").join(
                SQL(
                    "date_disposal = COALESCE(legacy.date_disposal, asset.date_disposal)"
                )
                if column == "date_disposal"
                else SQL(
                    "%s = legacy.%s", SQL.identifier(column), SQL.identifier(column)
                )
                for column in present
            ),
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )
    # The core asset refuses a disposal before its acquisition; a gross increase
    # closed with its parent can carry one.
    cr.execute(
        SQL(
            """
            UPDATE resource_asset asset
               SET date_disposal = asset.date_acquisition
              FROM %s map
             WHERE asset.id = map.resource_asset_id
               AND asset.date_disposal < asset.date_acquisition
            """,
            SQL.identifier(MAP_TABLE),
        )
    )
    cr.execute(
        SQL(
            """
            UPDATE resource_asset asset
               SET state = CASE legacy.depreciation_state
                               WHEN 'close' THEN 'disposed'
                               WHEN 'open' THEN CASE WHEN map.created OR asset.state = 'draft' THEN 'in_service' ELSE asset.state END
                               WHEN 'paused' THEN CASE WHEN map.created OR asset.state = 'draft' THEN 'in_service' ELSE asset.state END
                               ELSE asset.state
                           END
              FROM %(legacy)s legacy
              JOIN %(map)s map ON map.account_asset_id = legacy.id
             WHERE asset.id = map.resource_asset_id
            """,
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )


def _repoint_entries(cr):
    if column_exists(cr, "account_move", "legacy_depreciation_asset_id"):
        # The field is gone, so the ORM no longer creates this column; it is
        # the hand-off 1.5 reads to set depreciation_board_id, and 1.6 drops it.
        cr.execute(
            "ALTER TABLE account_move ADD COLUMN IF NOT EXISTS depreciation_asset_id int4"
        )
        cr.execute(
            SQL(
                """
                UPDATE account_move move
                   SET depreciation_asset_id = map.resource_asset_id
                  FROM %s map
                 WHERE map.account_asset_id = move.legacy_depreciation_asset_id
                """,
                SQL.identifier(MAP_TABLE),
            )
        )
        cr.execute("ALTER TABLE account_move DROP COLUMN legacy_depreciation_asset_id")
    if table_exists(cr, "legacy_asset_move_line_rel"):
        # 1.5 moves this relation onto the board; until then it is the
        # asset's, and the ORM no longer creates it.
        cr.execute(
            """
            CREATE TABLE IF NOT EXISTS asset_move_line_rel (
                asset_id integer NOT NULL,
                line_id integer NOT NULL,
                PRIMARY KEY (asset_id, line_id)
            )
            """
        )
        cr.execute(
            SQL(
                """
                INSERT INTO asset_move_line_rel (asset_id, line_id)
                SELECT map.resource_asset_id, rel.line_id
                  FROM legacy_asset_move_line_rel rel
                  JOIN %s map ON map.account_asset_id = rel.asset_id
                ON CONFLICT DO NOTHING
                """,
                SQL.identifier(MAP_TABLE),
            )
        )
        cr.execute("DROP TABLE legacy_asset_move_line_rel")


def _repoint_references(env):
    cr = env.cr
    for table, model_column in GENERIC_REFERENCES:
        if not table_exists(cr, table):
            continue
        if table == "mail_followers":
            cr.execute(
                SQL(
                    """
                    DELETE FROM mail_followers follower
                     USING %(map)s map
                     WHERE follower.res_model = 'account.asset'
                       AND follower.res_id = map.account_asset_id
                       AND EXISTS (SELECT 1 FROM mail_followers kept
                                    WHERE kept.res_model = 'resource.asset'
                                      AND kept.res_id = map.resource_asset_id
                                      AND kept.partner_id = follower.partner_id)
                    """,
                    map=SQL.identifier(MAP_TABLE),
                )
            )
        cr.execute(
            SQL(
                """
                UPDATE %(table)s record
                   SET %(model)s = 'resource.asset', res_id = map.resource_asset_id
                  FROM %(map)s map
                 WHERE record.%(model)s = 'account.asset'
                   AND record.res_id = map.account_asset_id
                """,
                table=SQL.identifier(table),
                model=SQL.identifier(model_column),
                map=SQL.identifier(MAP_TABLE),
            )
        )
    if column_exists(cr, "mail_activity", "res_model_id"):
        cr.execute(
            """
            UPDATE mail_activity
               SET res_model_id = (SELECT id FROM ir_model WHERE model = 'resource.asset')
             WHERE res_model = 'resource.asset'
               AND res_model_id = (SELECT id FROM ir_model WHERE model = 'account.asset')
            """
        )
    cr.execute(
        """
        UPDATE mail_tracking_value tracking
           SET field_id = target.id
          FROM ir_model_fields source, ir_model_fields target
         WHERE tracking.field_id = source.id
           AND source.model = 'account.asset'
           AND target.model = 'resource.asset'
           AND target.name = source.name
        """
    )
    cr.execute(
        "UPDATE ir_filters SET model_id = 'resource.asset' WHERE model_id = 'account.asset'"
    )


def _merge_definitions_onto_kinds(env):
    cr = env.cr
    definitions = {}
    if column_exists(cr, "account_depreciation_profile", "asset_properties_definition"):
        cr.execute(
            "SELECT id, asset_properties_definition FROM account_depreciation_profile WHERE asset_properties_definition IS NOT NULL"
        )
        definitions.update(dict(cr.fetchall()))
    if table_exists(cr, "account_depreciation_profile_definition_stash"):
        cr.execute(
            "SELECT profile_id, definition FROM account_depreciation_profile_definition_stash"
        )
        definitions.update(dict(cr.fetchall()))
        cr.execute("DROP TABLE account_depreciation_profile_definition_stash")
    definitions = {profile: value for profile, value in definitions.items() if value}
    if not definitions:
        return
    cr.execute(
        SQL(
            """
            SELECT DISTINCT asset.depreciation_profile_id, asset.kind_id
              FROM resource_asset asset
              JOIN %s map ON map.resource_asset_id = asset.id
             WHERE asset.depreciation_profile_id = ANY(%s)
            """,
            SQL.identifier(MAP_TABLE),
            list(definitions),
        )
    )
    for profile_id, kind_id in cr.fetchall():
        cr.execute(
            "SELECT asset_properties_definition FROM resource_asset_kind WHERE id = %s",
            (kind_id,),
        )
        current = cr.fetchone()[0] or []
        names = {prop.get("name") for prop in current}
        merged = current + [
            prop for prop in definitions[profile_id] if prop.get("name") not in names
        ]
        cr.execute(
            "UPDATE resource_asset_kind SET asset_properties_definition = %s WHERE id = %s",
            (psycopg.types.json.Jsonb(merged), kind_id),
        )

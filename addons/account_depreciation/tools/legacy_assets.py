from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

LEGACY_TABLE = "legacy_account_asset"
MAP_TABLE = "account_depreciation_asset_map"


def has_legacy_assets(cr):
    return table_exists(cr, LEGACY_TABLE) and table_exists(cr, MAP_TABLE)


def copy_legacy_columns(cr, columns):
    # Called from each dependant's own post-migrate: account_depreciation's post
    # runs before a dependant is loaded, when its columns do not exist yet.
    if not has_legacy_assets(cr):
        return 0
    pairs = {
        legacy: new
        for legacy, new in columns.items()
        if column_exists(cr, LEGACY_TABLE, legacy)
        and column_exists(cr, "resource_asset", new)
    }
    if not pairs:
        return 0
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
                SQL("%s = legacy.%s", SQL.identifier(new), SQL.identifier(legacy))
                for legacy, new in pairs.items()
            ),
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )
    return cr.rowcount


def legacy_rows(cr, columns):
    if not has_legacy_assets(cr):
        return
    present = [column for column in columns if column_exists(cr, LEGACY_TABLE, column)]
    if not present:
        return
    cr.execute(
        SQL(
            """
            SELECT map.resource_asset_id, %(columns)s
              FROM %(legacy)s legacy
              JOIN %(map)s map ON map.account_asset_id = legacy.id
          ORDER BY map.resource_asset_id
            """,
            columns=SQL(", ").join(
                SQL("legacy.%s", SQL.identifier(column)) for column in present
            ),
            legacy=SQL.identifier(LEGACY_TABLE),
            map=SQL.identifier(MAP_TABLE),
        )
    )
    for row in cr.fetchall():
        yield row[0], dict(zip(present, row[1:], strict=True))

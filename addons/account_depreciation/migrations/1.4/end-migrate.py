from odoo.tools import SQL

from odoo.addons.account_depreciation.tools.legacy_assets import LEGACY_TABLE, MAP_TABLE


def migrate(cr, version):
    if not version:
        return
    for table in (MAP_TABLE, LEGACY_TABLE):
        cr.execute(SQL("DROP TABLE IF EXISTS %s CASCADE", SQL.identifier(table)))

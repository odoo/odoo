from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "account_depreciation_board", ["increased_asset_id"])
    schema.drop_columns(cr, "account_move", ["depreciation_asset_id"])

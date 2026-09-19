from odoo.addons.resource_asset.table_inheritance import move_rows_into_subtype_table


def migrate(cr, version):
    move_rows_into_subtype_table(cr, "room", "resource_asset_room")

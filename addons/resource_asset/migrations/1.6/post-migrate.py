from odoo.db.schema import column_exists


def migrate(cr, version):
    if column_exists(cr, "resource_asset_kind", "model_name"):
        cr.execute("ALTER TABLE resource_asset_kind DROP COLUMN model_name")

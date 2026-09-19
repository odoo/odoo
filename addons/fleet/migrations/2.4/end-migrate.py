from odoo.db.schema import column_exists


def migrate(cr, version):
    if column_exists(cr, "resource_asset", "is_vehicle"):
        cr.execute("ALTER TABLE resource_asset DROP COLUMN is_vehicle")

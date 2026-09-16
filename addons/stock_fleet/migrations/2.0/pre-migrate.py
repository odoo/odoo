from odoo.db.schema import column_exists, rename_column


def migrate(cr, version):
    if version and column_exists(cr, "stock_picking_batch", "vehicle_id"):
        rename_column(cr, "stock_picking_batch", "vehicle_id", "legacy_vehicle_id")

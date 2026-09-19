from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "repair_order", ["location_dest_id", "parts_location_id"])

from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "appointment_booking_line", ["appointment_type_id"])

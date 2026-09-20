from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "event_booth_registration", ["partner_id"])
    schema.drop_columns(cr, "event_type_booth", ["price"])

from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "event_event", ["country_id"])
    schema.drop_columns(cr, "event_registration", ["company_id"])
    schema.drop_columns(cr, "event_tag", ["category_sequence"])

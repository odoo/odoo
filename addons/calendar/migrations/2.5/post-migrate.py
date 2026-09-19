from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "appointment_booking_line", ["event_start", "event_stop"])
    schema.drop_columns(cr, "calendar_event", ["res_model"])
    schema.drop_columns(cr, "survey_user_input_line", ["appointment_type_id", "partner_id"])

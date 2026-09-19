from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(
        cr, "survey_user_input_line", ["survey_id", "question_sequence"]
    )

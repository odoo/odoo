from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "hr_work_entry", ["department_id"])

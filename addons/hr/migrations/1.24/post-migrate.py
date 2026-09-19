from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "hr_employee", ["birthday"])
    schema.drop_columns(cr, "hr_employee_change_request", ["company_id"])

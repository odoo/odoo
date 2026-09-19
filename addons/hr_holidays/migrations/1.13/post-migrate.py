from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "hr_leave", ["user_id", "employee_company_id"])
    schema.drop_columns(cr, "hr_leave_allocation", ["employee_company_id"])

from odoo.db.schema import column_exists

COLUMNS = (
    "hr_presence_control_email_amount",
    "hr_presence_control_ip_list",
    "employee_properties_definition",
    "hr_presence_control_login",
    "hr_presence_control_email",
    "hr_presence_control_ip",
    "hr_presence_control_attendance",
    "contract_expiration_notice_period",
    "work_permit_expiration_notice_period",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")

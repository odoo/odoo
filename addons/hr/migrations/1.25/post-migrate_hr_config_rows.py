from odoo import SUPERUSER_ID, api
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
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    if not present:
        return
    # the rows through the ORM, so every default and required value is
    # applied; the values by SQL, straight from the company's columns
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].with_context(active_test=False).search([])
    env["hr.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE hr_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()

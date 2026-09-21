from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

COLUMNS = (
    "hr_attendance_display_overtime",
    "attendance_kiosk_mode",
    "attendance_barcode_source",
    "attendance_kiosk_delay",
    "attendance_kiosk_key",
    "attendance_kiosk_use_pin",
    "attendance_from_systray",
    "attendance_overtime_validation",
    "auto_check_out",
    "auto_check_out_tolerance",
    "absence_management",
    "attendance_device_tracking",
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
    env["hr_attendance.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE hr_attendance_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()

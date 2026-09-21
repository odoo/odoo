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
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")

from odoo import models
from odoo.exceptions import AccessError
from odoo.tools import py_to_js_locale


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_attendance_kiosk_info(self):
        self.ensure_one()
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(self.env._("Only Point of Sale users can open the attendance kiosk."))
        company = self.company_id.sudo()
        departments = self.env["hr.department"].sudo().with_context(allowed_company_ids=company.ids).search_fetch(
            [("company_id", "=", company.id)],
            ["name", "total_employee"],
        )
        return {
            "token": company.attendance_kiosk_key,
            "companyId": company.id,
            "companyName": company.name,
            "departments": [{"id": dep.id, "name": dep.name, "count": dep.total_employee} for dep in departments],
            "kioskMode": company.attendance_kiosk_mode,
            "barcodeSource": company.attendance_barcode_source,
            "fromTrialMode": False,
            "deviceTrackingEnabled": company.attendance_device_tracking,
            "captureCheckInImage": company.attendance_capture_check_in,
            "lang": py_to_js_locale(self.env.lang),
        }

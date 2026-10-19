# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def lazy_session_info(self):
        res = super().lazy_session_info()
        if self.env.user and self.env.user.employee_id:
            employee = self.env.user.employee_id
            company = employee.company_id
            res.update({
                'attendance_state': employee.attendance_state,
                'attendance_check_in_ability': employee._has_attendance_check_in_ability(),
                'attendance_device_tracking': company.attendance_device_tracking,
                'attendance_capture_check_in': company.attendance_capture_check_in,
                'attendance_break_management': company.attendance_break_management,
            })
        return res

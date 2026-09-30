# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_attendance.controllers.main import HrAttendance
from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def lazy_session_info(self):
        res = super().lazy_session_info()
        if self.env.user and self.env.user.employee_id:
            employee = self.env.user.employee_id
            res['attendance_user_data'] = HrAttendance._get_user_attendance_data(employee)
        return res

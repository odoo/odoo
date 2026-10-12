# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not (
            self.env.user.has_group('hr_attendance.group_hr_attendance_manager') and
            self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        ):
            res.append(self.env.ref('hr_holidays_attendance.hr_leave_attendance_report').id)
        return res

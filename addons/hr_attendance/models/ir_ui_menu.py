# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if self.env.user.has_group('hr_attendance.group_hr_attendance_user'):
            res.append(self.env.ref('hr_attendance.menu_hr_attendance_attendances_overview').id)
        return res

    @api.model
    def get_user_roots(self):
        kiosk = self.browse()
        if self.env.user.has_group('hr_attendance.group_hr_attendance_user'):
            kiosk = self.env.ref('hr_attendance.menu_hr_attendance_kiosk')
        return super().get_user_roots() - kiosk

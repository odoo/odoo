# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        att_menu = self.env.ref('hr_attendance.menu_hr_attendance_attendances_overview', raise_if_not_found=False)
        if att_menu and self.env.user.has_group('hr_attendance.group_hr_attendance_user'):
            res.append(att_menu.id)
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver'):
            res.append(self.env.ref('hr_timesheet.timesheet_menu_activity_user').id)
        return res

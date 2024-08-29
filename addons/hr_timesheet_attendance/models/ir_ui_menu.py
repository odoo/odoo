# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model, base.IrUiMenu):

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not (self.env.user.has_group('hr_timesheet.group_hr_timesheet_user')):
            res.append(self.env.ref('hr_timesheet_attendance.menu_hr_timesheet_attendance_report').id)
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not (self.env.user.has_group('planning.group_planning_manager') and self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')):
            res.append(self.env.ref('project_timesheet_forecast.menu_project_timesheet_forecast_report_analysis').id)
        return res

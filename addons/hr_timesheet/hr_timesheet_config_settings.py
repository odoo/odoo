# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimesheetConfiguration(models.TransientModel):
    _name = 'hr.timesheet.config.settings'
    _inherit = 'base.config.settings'

    module_project_timesheet_synchro = fields.Boolean("Awesome Timesheet")
    module_sale_timesheet = fields.Boolean("Time Billing")
    module_project_forecast = fields.Boolean(string="Forecasts")
    module_hr_expense = fields.Boolean("Expenses")
    module_hr_holidays = fields.Boolean("Leave Management")
    module_hr_timesheet_attendance = fields.Boolean("Attendances")

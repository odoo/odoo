# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectConfiguration(models.TransientModel):
    _name = 'project.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    module_pad = fields.Boolean("Collaborative Pads")
    module_hr_timesheet = fields.Boolean("Timesheets")
    module_project_timesheet_synchro = fields.Boolean("Awesome Timesheet")
    module_rating_project = fields.Boolean(string="Rating on Tasks")
    module_project_forecast = fields.Boolean(string="Forecasts")
    module_hr_holidays = fields.Boolean("Leave Management")
    module_hr_timesheet_attendance = fields.Boolean("Attendances")
    module_sale_timesheet = fields.Boolean("Time Billing")
    module_hr_expense = fields.Boolean("Expenses")
    module_project_issue = fields.Boolean("Issue Tracking")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")

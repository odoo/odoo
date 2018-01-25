# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_timesheet = fields.Boolean("Timesheets")
    module_project_forecast = fields.Boolean(string="Forecasts")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")
    group_project_rating = fields.Boolean("Use Rating on Project", implied_group='project.group_project_rating')
    project_time_mode_id = fields.Many2one(
        'product.uom', related='company_id.project_time_mode_id', string='Project Time Unit',
        help="This will set the unit of measure used in projects and tasks.\n"
             "If you use the timesheet linked to projects, don't "
             "forget to setup the right unit of measure in your employees.")

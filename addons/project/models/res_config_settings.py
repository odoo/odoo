# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    module_pad = fields.Boolean("Collaborative Pads")
    module_hr_timesheet = fields.Boolean("Timesheets")
    module_rating_project = fields.Boolean(string="Rating on Tasks")
    module_project_forecast = fields.Boolean(string="Forecasts")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_forecast = fields.Boolean(string="Project Planning", default=False)
    planning_generation_interval = fields.Integer("Rate Of Shift Generation", required=True,
        related="company_id.planning_generation_interval", readonly=False)

    planning_employee_unavailabilities = fields.Selection(
        related="company_id.planning_employee_unavailabilities",
        readonly=False,
    )

    planning_self_unassign_days_before = fields.Integer(
        "Days before shift for unassignment",
        related="company_id.planning_self_unassign_days_before",
        readonly=False
    )

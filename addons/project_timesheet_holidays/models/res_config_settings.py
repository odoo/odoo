# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    leave_timesheet_project_id = fields.Many2one(related='company_id.leave_timesheet_project_id', string="Internal Project", domain="[('is_template', '=', False), ('company_id', '=', company_id)]", readonly=False)
    leave_timesheet_task_id = fields.Many2one(related='company_id.leave_timesheet_task_id', string="Time Off Task", domain="[('is_template', '=', False), ('company_id', '=', company_id)]", readonly=False)

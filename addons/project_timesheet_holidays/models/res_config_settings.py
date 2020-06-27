# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    leave_timesheet_project_id = fields.Many2one(
        related='company_id.leave_timesheet_project_id', required=True, string="Internal Project",
        domain="[('company_id', '=', company_id)]", readonly=False)
    leave_timesheet_task_id = fields.Many2one(
        related='company_id.leave_timesheet_task_id', string="Time Off Task", readonly=False,
        domain="[('company_id', '=', company_id), ('project_id', '=?', leave_timesheet_project_id)]")

    @api.onchange('leave_timesheet_project_id')
    def _onchange_timesheet_project_id(self):
        if self.leave_timesheet_project_id != self.leave_timesheet_task_id.project_id:
            self.leave_timesheet_task_id = False

    @api.onchange('leave_timesheet_task_id')
    def _onchange_timesheet_task_id(self):
        if self.leave_timesheet_task_id:
            self.leave_timesheet_project_id = self.leave_timesheet_task_id.project_id

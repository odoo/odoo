# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class project_issue(models.Model):
    _inherit = 'project.issue'
    _description = 'project issue'

    progress = fields.Float(compute='_hours_get', string='Progress (%)', group_operator="avg", store=True, help="Computed as: Time Spent / Total Time.")
    timesheet_ids = fields.One2many('account.analytic.line', 'issue_id', string='Timesheets')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.depends('task_id')
    def _hours_get(self):
        for issue in self:
            issue.progress = issue.task_id.progress

    @api.multi
    def on_change_project(self, project_id):
        if not project_id:
            return {'value': {'analytic_account_id': False}}

        result = super(project_issue, self).on_change_project(project_id)
        
        project = self.env['project.project'].browse(project_id)
        if 'value' not in result:
            result['value'] = {}

        account = project.analytic_account_id
        if account:
            result['value']['analytic_account_id'] = account.id
        return result


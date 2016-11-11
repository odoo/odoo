#-*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    progress = fields.Float(related='task_id.progress', store=True, string='Progress (%)', multi='line_id', group_operator="avg", help="Computed as: Time Spent / Total Time.")
    timesheet_ids = fields.One2many('account.analytic.line', 'issue_id', 'Timesheets')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        super(ProjectIssue, self)._onchange_project_id()
        if not self.project_id:
            self.analytic_account_id = False
        else:
            account = self.project_id.analytic_account_id
            if account:
                self.analytic_account_id = account.id

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    is_timesheet = fields.Boolean(string="Is a Timesheet")
    task_id = fields.Many2one('project.task', 'Task')
    project_id = fields.Many2one('project.project', 'Project')

    # Constraint: if aal is a timesheet, then project_id is required
    _sql_constraints = [
        ('check_project', "CHECK( (is_timesheet=TRUE AND project_id IS NOT NULL) or (is_timesheet=FALSE) )", 'Timesheets activities must be linked to a project'),
    ]

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.task_id = False
        if self.project_id:
            self.account_id = self.project_id.analytic_account_id.id

    @api.model
    def create(self, vals):
        if vals.get('is_timesheet') and not vals.get('account_id'):
            if vals.get('project_id'):
                project = self.env['project.project'].search([('id', '=', vals.get('project_id'))])
                vals['account_id'] = project.analytic_account_id.id
            else:
                raise UserError(_('You must select a project'))
        return super(AccountAnalyticLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].search([('id', '=', vals.get('project_id'))])
            vals['account_id'] = project.analytic_account_id.id
        return super(AccountAnalyticLine, self).write(vals)

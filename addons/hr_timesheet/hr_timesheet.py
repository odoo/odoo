# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    task_id = fields.Many2one('project.task', 'Task')
    project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True)

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.task_id = False

    @api.depends('user_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.user_id.employee_ids[:1].department_id

    @api.model
    def create(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
        return super(AccountAnalyticLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
        return super(AccountAnalyticLine, self).write(vals)

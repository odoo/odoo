# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_employee_id(self):
        return self.env.user.employee_ids[0]

    task_id = fields.Many2one('project.task', 'Task')
    project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])

    employee_id = fields.Many2one('hr.employee', "Employee", default=_default_employee_id)
    department_id = fields.Many2one('hr.department', "Department", related='employee_id.department_id', store=True, readonly=True)

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.task_id = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.user_id = self.employee_id.user_id

    @api.model
    def create(self, vals):
        vals = self._update_timesheet_values(vals)
        return super(AccountAnalyticLine, self).create(vals)

    @api.multi
    def write(self, vals):
        vals = self._update_timesheet_values(vals)
        return super(AccountAnalyticLine, self).write(vals)

    def _update_timesheet_values(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals['user_id'] = employee.user_id.id
        return vals

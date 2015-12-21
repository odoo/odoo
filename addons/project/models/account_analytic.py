# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    use_tasks = fields.Boolean('Tasks', help="Check this box to manage internal activities through this project")
    company_uom_id = fields.Many2one(related='company_id.project_time_mode_id', string="Company UOM")


    @api.model
    def _trigger_project_creation(self, vals):
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        return vals.get('use_tasks') and not 'project_creation_in_progress' in self.env.context

    def project_create(self, vals):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        Project = self.env['project.project']
        projects = Project.search([('analytic_account_id','=', self.id)])
        if not projects and self._trigger_project_creation(vals):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': self.id,
                'use_tasks': True,
            }
            return Project.create(project_values)

    @api.model
    def create(self, vals):
        if vals.get('child_ids') and self.env.context.get('analytic_project_copy'):
            vals['child_ids'] = []
        analytic_account = super(AccountAnalyticAccount, self).create(vals)
        analytic_account.project_create(vals)
        return analytic_account

    @api.multi
    def write(self, vals):
        vals_for_project = vals.copy()
        for analytic in self:
            if not vals.get('name'):
                vals_for_project['name'] = analytic.name
            analytic.project_create(vals_for_project)
        return super(AccountAnalyticAccount, self).write(vals)

    @api.multi
    def unlink(self):
        tasks_count = self.env['project.task'].search_count([('project_id.analytic_account_id', 'in', self.ids)])
        if tasks_count:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(AccountAnalyticAccount, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('current_model') == 'project.project':
            analytic_account = self.search(args + [('name', operator, name)], limit=limit)
            return analytic_account.name_get()

        return super(AccountAnalyticAccount, self).name_search(name, args=args, operator=operator, limit=limit)

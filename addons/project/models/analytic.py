# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    company_uom_id = fields.Many2one('product.uom', related='company_id.project_time_mode_id', string="Company UOM")
    project_ids = fields.One2many('project.project', 'analytic_account_id', string='Projects')
    project_count = fields.Integer("Project Count", compute='_compute_project_count')

    def _compute_project_count(self):
        for account in self:
            account.project_count = len(account.with_context(active_test=False).project_ids)

    @api.multi
    def unlink(self):
        projects = self.env['project.project'].search([('analytic_account_id', 'in', self.ids)])
        has_tasks = self.env['project.task'].search_count([('project_id', 'in', projects.ids)])
        if has_tasks:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(AccountAnalyticAccount, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if self.env.context.get('current_model') == 'project.project':
            return self.search(args + [('name', operator, name)], limit=limit).name_get()

        return super(AccountAnalyticAccount, self).name_search(name, args=args, operator=operator, limit=limit)

    @api.multi
    def projects_action(self):
        projects = self.with_context(active_test=False).mapped('project_ids')
        result = {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "in", projects.ids]],
            "context": {"create": False},
            "name": "Projects",
        }
        if len(projects) == 1:
            result['views'] = [(False, "form")]
            result['res_id'] = projects.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

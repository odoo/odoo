# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    project_ids = fields.One2many('project.project', 'account_id', string='Projects', export_string_translation=False)
    project_count = fields.Integer("Project Count", compute='_compute_project_count', export_string_translation=False)

    @api.depends('project_ids')
    def _compute_project_count(self):
        project_data = self.env['project.project']._read_group([('account_id', 'in', self.ids)], ['account_id'], ['__count'])
        mapping = {analytic_account.id: count for analytic_account, count in project_data}
        for account in self:
            account.project_count = mapping.get(account.id, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_existing_tasks(self):
        projects = self.env['project.project'].search([('account_id', 'in', self.ids)])
        has_tasks = self.env['project.task'].search_count([('project_id', 'in', projects.ids)])
        if has_tasks:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))

    def action_view_projects(self):
        kanban_view_id = self.env.ref('project.view_project_kanban').id
        result = {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "views": [[kanban_view_id, "kanban"], [False, "form"]],
            "domain": [['account_id', '=', self.id]],
            "context": {"create": False},
            "name": _("Projects"),
        }
        if len(self.project_ids) == 1:
            result['views'] = [(False, "form")]
            result['res_id'] = self.project_ids.id
        return result

    @api.constrains('plan_id')
    def _ensure_project_plan_consistency(self):

        plan_column_names = self.env['project.project']._get_plan_fnames()
        # It's cleaner to use the 'auto_account_id' to do this search, but using it causes issues at install with demo data
        domain = OR([[(fname, 'in', self.ids)] for fname in plan_column_names])
        projects = self.env['project.project'].search(domain)
        if not projects:
            return
        for project in projects:
            for plan_column_name in plan_column_names:
                account = project[plan_column_name]
                if account and account.id in self.ids and account.root_plan_id._column_name() != plan_column_name:
                    raise UserError(_("The account '%(account_name)s' is linked to the project '%(project_name)s'. "
                                            "Unlink it from its project before updating its plan.",
                                            account_name=account.name, project_name=project.name))

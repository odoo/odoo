# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class Project(models.Model):
    _inherit = 'project.project'

    expenses_count = fields.Integer('# Expenses', compute='_compute_expenses_count', groups='hr_expense.group_hr_expense_team_approver')

    @api.depends('analytic_account_id')
    def _compute_expenses_count(self):
        expenses_data = self.env['hr.expense']._read_group([
            ('analytic_account_id', '!=', False),
            ('analytic_account_id', 'in', self.analytic_account_id.ids)
        ],
        ['analytic_account_id'], ['analytic_account_id'])
        mapped_data = {data['analytic_account_id'][0]: data['analytic_account_id_count'] for data in expenses_data}
        for project in self:
            project.expenses_count = mapped_data.get(project.analytic_account_id.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    def action_open_project_expenses(self):
        expenses = self.env['hr.expense'].search([
            ('analytic_account_id', '!=', False),
            ('analytic_account_id', 'in', self.analytic_account_id.ids)
        ])
        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.hr_expense_actions_all")
        action.update({
            'display_name': _('Expenses'),
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban'], [False, 'graph'], [False, 'pivot']],
            'context': {'default_analytic_account_id': self.analytic_account_id.id},
            'domain': [('id', 'in', expenses.ids)]
        })
        if(len(expenses) == 1):
            action["views"] = [[False, 'form']]
            action["res_id"] = expenses.id
        return action

    # ----------------------------
    #  Project Update
    # ----------------------------
    def _get_expenses_profitability_items(self):
        if not self.analytic_account_id:
            return {}
        expenses_read_group = self.env['hr.expense'].sudo()._read_group(
            [('analytic_account_id', 'in', self.analytic_account_id.ids),
             ('is_refused', '=', False),
             ('state', 'in', ['approved', 'done'])],
            ['untaxed_amount'],
            [],
        )
        if not expenses_read_group or not expenses_read_group[0]['__count']:
            return {}
        expense_data = expenses_read_group[0]
        section_id = 'expenses'
        return {
            'costs': {'id': section_id, 'billed': -expense_data['untaxed_amount'], 'to_bill': 0.0},
        }

    def _get_profitability_items(self, with_action=True):
        profitability_data = super()._get_profitability_items(with_action)
        expenses_data = self._get_expenses_profitability_items(with_action)
        if expenses_data:
            if 'revenues' in expenses_data:
                revenues = profitability_data['revenues']
                revenues['data'].append(expenses_data['revenues'])
                revenues['total'] = {k: revenues['total'][k] + expenses_data['revenues'][k] for k in ['invoiced', 'to_invoice']}
            costs = profitability_data['costs']
            costs['data'].append(expenses_data['costs'])
            costs['total'] = {k: costs['total'][k] + expenses_data['costs'][k] for k in ['billed', 'to_bill']}
        return profitability_data

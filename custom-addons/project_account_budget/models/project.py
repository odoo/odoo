# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json

from odoo import api, fields, models, _
from odoo.osv import expression

class Project(models.Model):
    _inherit = "project.project"

    total_planned_amount = fields.Monetary(compute="_compute_total_planned_amount")
    total_practical_amount = fields.Monetary(related='analytic_account_id.total_practical_amount')
    total_budget_progress = fields.Monetary(compute="_compute_total_budget_progress")
    budget = fields.Integer('Total planned amount', compute='_compute_budget', default=0)

    @api.depends('analytic_account_id')
    def _compute_budget(self):
        budget_items = self.env['crossovered.budget.lines'].sudo()._read_group([
            ('analytic_account_id', 'in', self.analytic_account_id.ids),
        ], ['analytic_account_id'], ['planned_amount:sum'])
        budget_items_by_account_analytic = {analytic_account.id: planned_amount_sum for analytic_account, planned_amount_sum in budget_items}
        for project in self:
            project.budget = budget_items_by_account_analytic.get(project.analytic_account_id.id, 0.0)

    def _compute_total_planned_amount(self):
        budget_read_group = self.env['crossovered.budget.lines'].sudo()._read_group(
            [
                ('crossovered_budget_id.state', 'not in', ['draft', 'cancel']),
                ('analytic_account_id', 'in', self.analytic_account_id.ids)
            ],
            ['analytic_account_id'],
            ['planned_amount:sum'],
        )
        planned_amount_per_account_id = {
            analytic_account.id: planned_amount_sum
            for analytic_account, planned_amount_sum in budget_read_group
        }
        for project in self:
            project.total_planned_amount = planned_amount_per_account_id.get(project.analytic_account_id.id, 0)

    @api.depends('total_practical_amount', 'total_planned_amount')
    def _compute_total_budget_progress(self):
        for project in self:
            project.total_budget_progress = project.total_planned_amount and\
                (project.total_practical_amount - project.total_planned_amount) / abs(project.total_planned_amount)

    def action_view_budget_lines(self, domain=None):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "crossovered.budget.lines",
            "domain": expression.AND([
                [('analytic_account_id', '=', self.analytic_account_id.id), ('crossovered_budget_id.state', 'not in', ['draft', 'cancel'])],
                domain or [],
            ]),
            'context': {'create': False, 'edit': False},
            "name": _("Budget Items"),
            'view_mode': 'tree',
            'views': [
                [self.env.ref('project_account_budget.crossovered_budget_lines_view_tree_inherit').id, 'tree']
            ]
        }

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        panel_data['analytic_account_id'] = self.analytic_account_id.id
        panel_data['budget_items'] = self._get_budget_items()
        return panel_data

    def get_budget_items(self):
        self.ensure_one()
        if self.analytic_account_id and self.user_has_groups('project.group_project_user'):
            return self._get_budget_items(True)
        return {}

    def _get_budget_items(self, with_action=True):
        self.ensure_one()
        if not self.analytic_account_id:
            return
        budget_lines = self.env['crossovered.budget.lines'].sudo()._read_group(
            [
                ('analytic_account_id', '=', self.analytic_account_id.id),
                ('crossovered_budget_id', '!=', False),
                ('crossovered_budget_id.state', 'not in', ['draft', 'cancel']),
            ],
            ['general_budget_id', 'crossovered_budget_id', 'company_id'],
            ['planned_amount:sum', 'practical_amount:sum', 'id:array_agg'],
        )
        has_company_access = False
        for line in budget_lines:
            if line[2].id in self.env.context.get('allowed_company_ids', []):
                has_company_access = True
                break
        total_allocated = total_spent = 0.0
        can_see_budget_items = with_action and has_company_access and self.user_has_groups('account.group_account_readonly,analytic.group_analytic_accounting')
        budget_data_per_budget = defaultdict(
            lambda: {
                'allocated': 0,
                'spent': 0,
                **({
                    'ids': [],
                    'budgets': [],
                } if can_see_budget_items else {})
            }
        )

        for general_budget, crossovered_budget, dummy, allocated, spent, ids in budget_lines:
            budget_data = budget_data_per_budget[general_budget]
            budget_data['id'] = general_budget.id
            budget_data['name'] = general_budget.display_name
            budget_data['allocated'] += allocated
            budget_data['spent'] += spent
            total_allocated += allocated
            total_spent += spent

            if can_see_budget_items:
                budget_item = {
                    'id': crossovered_budget.id,
                    'name': crossovered_budget.display_name,
                    'allocated': allocated,
                    'spent': spent,
                    'progress': allocated and (spent - allocated) / abs(allocated),
                }
                budget_data['budgets'].append(budget_item)
                budget_data['ids'] += ids
            else:
                budget_data['budgets'] = []


        budget_data_per_budget = list(budget_data_per_budget.values())
        if can_see_budget_items:
            for budget_data in budget_data_per_budget:
                if len(budget_data['budgets']) == 1:
                    budget_data['budgets'].clear()
                budget_data['action'] = {
                    'name': 'action_view_budget_lines',
                    'type': 'object',
                    'domain': json.dumps([('id', 'in', budget_data.pop('ids'))]),
                }

        can_add_budget = with_action and self.user_has_groups('account.group_account_user')
        budget_items = {
            'data': budget_data_per_budget,
            'total': {
                'allocated': total_allocated,
                'spent': total_spent,
                'progress': total_allocated and (total_spent - total_allocated) / abs(total_allocated),
            },
            'can_add_budget': can_add_budget,
        }
        if can_add_budget:
            budget_items['form_view_id'] = self.env.ref('project_account_budget.crossovered_budget_view_form_dialog').id
            budget_items['company_id'] = self.company_id.id or self.env.company.id
        return budget_items

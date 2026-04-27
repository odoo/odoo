# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json

from odoo import fields, models, _
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    total_budget_amount = fields.Monetary('Total planned amount', compute='_compute_budget', default=0, export_string_translation=False)
    total_budget_progress = fields.Float("Budget Spent", compute="_compute_budget", export_string_translation=False)

    def _get_budget_analytic_account_domain(self):
        return expression.OR([
            [(account.plan_id._column_name(), '=', account.id)] for account in self.account_id
        ])

    def _compute_budget(self):
        budget_items = self.env['budget.line'].sudo()._read_group(
            self._get_budget_analytic_account_domain(),
            groupby=['account_id', 'budget_analytic_id'],
            aggregates=['budget_amount:sum', 'achieved_amount:sum'],
        )
        budget_items_by_account_analytic = defaultdict(lambda: {
            'budget_amount': 0,
            'budget_amount_for_progress': 0,
            'achieved_amount_for_progress': 0,
        })
        for analytic_account, budget_analytic_id, budget_amount_sum, achieved_amount_sum in budget_items:
            type_factor = -1 if budget_analytic_id.budget_type == 'expense' else 1
            budget_items_by_account_analytic[analytic_account.id]["budget_amount"] += budget_amount_sum
            budget_items_by_account_analytic[analytic_account.id]["budget_amount_for_progress"] += budget_amount_sum * type_factor
            budget_items_by_account_analytic[analytic_account.id]["achieved_amount_for_progress"] += achieved_amount_sum * type_factor

        for project in self:
            total_budget_amount = budget_items_by_account_analytic[project.account_id.id]['budget_amount']
            total_budget_amount_fp = budget_items_by_account_analytic[project.account_id.id]['budget_amount_for_progress']
            total_achieved_amount_fp = budget_items_by_account_analytic[project.account_id.id]['achieved_amount_for_progress']
            project.total_budget_progress = total_budget_amount_fp and (total_achieved_amount_fp - total_budget_amount_fp) / abs(total_budget_amount_fp)
            project.total_budget_amount = total_budget_amount

    def action_view_budget_lines(self, domain=None):
        self.ensure_one()
        budget_lines = self.env['budget.line'].search(expression.AND([
            [(self.account_id.plan_id._column_name(), '=', self.account_id.id), ('budget_analytic_id.state', 'in', ['confirmed', 'done'])],
            domain or [],
        ]))
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.analytic",
            "res_id": budget_lines.budget_analytic_id.id,
            'context': {'create': False, 'edit': False},
            "name": _("Budget Items"),
            'view_mode': 'form',
        }

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        panel_data['account_id'] = self.account_id.id
        panel_data['budget_items'] = self._get_budget_items()
        panel_data['show_budget_items'] = bool(self.account_id)
        return panel_data

    def get_budget_items(self):
        self.ensure_one()
        if self.account_id and self.env.user.has_group('project.group_project_user'):
            return self._get_budget_items(True)
        return {}

    def _get_budget_items(self, with_action=True):
        self.ensure_one()
        if not self.account_id:
            return
        budget_lines = self.env['budget.line'].sudo()._read_group(
            [
                (self.account_id.plan_id._column_name(), '=', self.account_id.id),
                ('budget_analytic_id', '!=', False),
                ('budget_analytic_id.state', 'in', ['confirmed', 'done']),
            ],
            ['budget_analytic_id', 'company_id'],
            ['budget_amount:sum', 'achieved_amount:sum', 'id:array_agg'],
        )
        has_company_access = False
        for line in budget_lines:
            if line[1].id in self.env.context.get('allowed_company_ids', []):
                has_company_access = True
                break
        total_allocated = total_spent = 0.0
        total_allocated_for_progress = total_spent_for_progress = 0.0
        can_see_budget_items = with_action and has_company_access and (
            self.env.user.has_group('account.group_account_readonly')
            or self.env.user.has_group('analytic.group_analytic_accounting')
        )
        budget_data_per_budget = defaultdict(
            lambda: {
                'allocated': 0,
                'spent': 0,
                'budget_type': False,
                **({
                    'ids': [],
                    'budgets': [],
                } if can_see_budget_items else {})
            }
        )

        for budget_analytic, dummy, allocated, spent, ids in budget_lines:
            budget_data = budget_data_per_budget[budget_analytic]
            budget_data['id'] = budget_analytic.id
            budget_data['name'] = budget_analytic.display_name
            budget_data['allocated'] += allocated
            budget_data['spent'] += spent
            budget_data['budget_type'] = budget_analytic.budget_type
            total_allocated += -allocated if budget_analytic.budget_type == 'expense' else allocated
            total_spent += -spent if budget_analytic.budget_type == 'expense' else spent
            total_allocated_for_progress += allocated * -1 if budget_analytic.budget_type == 'expense' else allocated
            total_spent_for_progress += spent * -1 if budget_analytic.budget_type == 'expense' else spent
            if can_see_budget_items:
                budget_item = {
                    'id': budget_analytic.id,
                    'name': budget_analytic.display_name,
                    'allocated': allocated,
                    'spent': spent,
                    'budget_type': budget_analytic.budget_type,
                    'progress': allocated and (spent - allocated) / abs(allocated) * (-1 if budget_analytic.budget_type == 'expense' else 1),
                }
                budget_data['budgets'].append(budget_item)
                budget_data['ids'] += ids
            else:
                budget_data['budgets'] = []

        for budget_data in budget_data_per_budget.values():
            budget_data['progress'] = budget_data['allocated'] and (budget_data['spent'] - budget_data['allocated']) / abs(budget_data['allocated']) \
                * (-1 if budget_data['budget_type'] == 'expense' else 1)

        budget_data_per_budget = list(budget_data_per_budget.values())
        if can_see_budget_items:
            for budget_data in budget_data_per_budget:
                if len(budget_data['budgets']) == 1:
                    budget_data['budgets'].clear()
                budget_data['action'] = {
                    'name': 'action_view_budget_lines',
                    'type': 'object',
                    'args': json.dumps([[('id', 'in', budget_data.pop('ids'))]]),
                }

        can_add_budget = with_action and self.env.user.has_group('account.group_account_user')
        budget_items = {
            'data': budget_data_per_budget,
            'total': {
                'allocated': total_allocated,
                'spent': total_spent,
                'progress': (total_spent_for_progress - total_allocated_for_progress) / abs(total_allocated_for_progress) if total_allocated_for_progress else 0,
            },
            'can_add_budget': can_add_budget,
        }
        if can_add_budget:
            budget_items['form_view_id'] = self.env.ref('project_account_budget.view_budget_analytic_form_dialog').id
            budget_items['company_id'] = self.company_id.id or self.env.company.id
        return budget_items

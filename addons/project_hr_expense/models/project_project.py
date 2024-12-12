# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.osv import expression


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # ----------------------------
    #  Actions
    # ----------------------------

    def _get_expense_action(self, domain=None, expense_ids=None):
        if not domain and not expense_ids:
            return {}
        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.hr_expense_actions_all")
        action.update({
            'display_name': self.env._('Expenses'),
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban'], [False, 'graph'], [False, 'pivot']],
            'context': {'project_id': self.id},
            'domain': domain or [('id', 'in', expense_ids)],
        })
        if not self.env.context.get('from_embedded_action') and len(expense_ids) == 1:
            action["views"] = [[False, 'form']]
            action["res_id"] = expense_ids[0]
        return action

    def _get_add_purchase_items_domain(self):
        return expression.AND([
            super()._get_add_purchase_items_domain(),
            [('expense_id', '=', False)],
        ])

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name == 'expenses':
            return self._get_expense_action(domain, [res_id] if res_id else [])
        return super().action_profitability_items(section_name, domain, res_id)

    def action_open_project_expenses(self):
        self.ensure_one()
        return self._get_expense_action(domain=[('analytic_distribution', 'in', self.account_id.ids)])

    # ----------------------------
    #  Project Update
    # ----------------------------

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['expenses'] = self.env._('Expenses')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['expenses'] = 13
        return sequence_per_invoice_type

    def _get_already_included_profitability_invoice_line_ids(self):
        # As both purchase orders and expenses (paid by employee) create vendor bills,
        # we need to make sure they are exclusive in the profitability report.
        move_line_ids = super()._get_already_included_profitability_invoice_line_ids()
        query = self.env['account.move.line'].sudo()._search([
            ('move_id.expense_sheet_id', '!=', False),
            ('id', 'not in', move_line_ids),
        ])
        return move_line_ids + list(query)

    def _get_expenses_profitability_items(self, with_action=True):
        if not self.account_id:
            return {}
        can_see_expense = with_action and self.env.user.has_group('hr_expense.group_hr_expense_team_approver')

        expenses = self.env['hr.expense'].search_fetch(
            domain=[
                ('sheet_id.state', 'in', ['post', 'done']),
                ('analytic_distribution', 'in', self.account_id.ids),
            ],
            field_names=['currency_id', 'untaxed_amount_currency', 'analytic_distribution']
        )
        if not expenses:
            return {}
        expense_ids = []
        amount_billed = 0.0
        for expense in expenses:
            # The analytic distribution can contain multiple contributions (percentages) for the same project but for different departments.
            # That's why here we look for each percentage that is related to this analytic account and we sum them all.
            analytic_contribution = sum(
                percentage
                for ids, percentage in expense.analytic_distribution.items()
                if str(self.account_id.id) in ids.split(",")
            ) / 100
            if can_see_expense:
                expense_ids.append(expense.id)
            amount_billed += (
                expense.currency_id._convert(
                    from_amount=expense.untaxed_amount_currency,
                    to_currency=self.currency_id,
                    company=self.company_id,
                ) * analytic_contribution
            )

        section_id = 'expenses'
        expense_profitability_items = {
            'costs': {'id': section_id, 'sequence': self._get_profitability_sequence_per_invoice_type()[section_id], 'billed': -amount_billed, 'to_bill': 0.0},
        }
        if can_see_expense:
            args = [section_id, [('id', 'in', expense_ids)]]
            if len(expense_ids) == 1:
                args.append(expense_ids[0])
            action = {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}
            expense_profitability_items['costs']['action'] = action
        return expense_profitability_items

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            ['|', ('move_line_id', '=', False), ('move_line_id.expense_id', '=', False)],
        ])

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

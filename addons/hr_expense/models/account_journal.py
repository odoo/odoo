from collections import defaultdict

from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        # Extends account
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        purchase_journals = self.filtered(lambda journal: journal.type == 'purchase')
        if not purchase_journals:
            return

        # Moves linked to expenses
        moves_expenses = self.env['account.move']._search([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', purchase_journals.ids),
            ('state', '=', 'draft'),
            ('expense_ids', '!=', False),
        ])
        sql = moves_expenses.select(*self._get_bills_field_list())
        res = self.env.execute_query_dict(sql)
        query_results_expenses = defaultdict(list)
        for vals in res:
            query_results_expenses[vals['journal_id']].append(vals)

        for journal in purchase_journals:
            currency = journal.currency_id or journal.company_id.sudo().currency_id.with_env(self.env)
            (number_expense, sum_expense) = self._count_results_and_sum_amounts(query_results_expenses[journal.id], currency)

            dashboard_data[journal.id].update({
                'number_expense': number_expense,
                'sum_expense': currency.format(sum_expense),
            })

    def open_draft_moves_linked_to_expense(self):
        self.ensure_one()
        return self.env['account.move']._get_records_action(
            name=self.env._("Expense linked moves"),
            target='main',
            views=[(False, 'list'), (False, 'form')],
            domain=[
                ('state', '=', 'draft'),
                ('journal_id', '=', self.id),
                ('expense_ids', '!=', False),
            ],
        )

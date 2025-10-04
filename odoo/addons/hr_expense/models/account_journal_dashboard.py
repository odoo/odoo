# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.account_journal_dashboard import group_by_journal


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _prepare_expense_sheet_data_domain(self):
        return [
            ('journal_id', 'in', self.ids),
            '|',
            ('state', '=', 'post'),
            '&',
            ('state', '=', 'done'),
            ('payment_state', '=', 'partial'),
        ]

    def _get_expense_to_pay_query(self):
        return self.env['hr.expense.sheet']._where_calc(self._prepare_expense_sheet_data_domain())

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super(AccountJournal, self)._fill_sale_purchase_dashboard_data(dashboard_data)
        sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        if not sale_purchase_journals:
            return
        field_list = [
            "hr_expense_sheet.journal_id",
            # todo master: "hr_expense_sheet.amount_residual AS amount_total_company",
            "hr_expense_sheet.total_amount AS amount_total_company",
            "hr_expense_sheet.currency_id AS currency",
        ]
        query, params = sale_purchase_journals._get_expense_to_pay_query().select(*field_list)
        self.env.cr.execute(query, params)
        query_results_to_pay = group_by_journal(self.env.cr.dictfetchall())
        for journal in sale_purchase_journals:
            currency = journal.currency_id or journal.company_id.currency_id
            (number_expenses_to_pay, sum_expenses_to_pay) = self._count_results_and_sum_amounts(query_results_to_pay[journal.id], currency)
            dashboard_data[journal.id].update({
                'number_expenses_to_pay': number_expenses_to_pay,
                'sum_expenses_to_pay': currency.format(sum_expenses_to_pay),
            })

    def open_expenses_action(self):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_expense.action_hr_expense_sheet_all_all')
        action['context'] = {
            'search_default_approved': 1,
            'search_default_to_post': 1,
            'search_default_journal_id': self.id,
            'default_journal_id': self.id,
        }
        action['view_mode'] = 'tree,form'
        action['views'] = [(k,v) for k,v in action['views'] if v in ['tree', 'form']]
        action['domain'] = self._prepare_expense_sheet_data_domain()
        return action

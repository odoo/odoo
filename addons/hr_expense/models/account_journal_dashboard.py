# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_expenses_to_pay_query(self):
        """
        Returns a tuple containing as it's first element the SQL query used to
        gather the expenses in reported state data, and the arguments
        dictionary to use to run it as it's second.
        """
        query = """SELECT total_amount as amount_total, currency_id AS currency
                  FROM hr_expense_sheet
                  WHERE state IN ('approve', 'post')
                  and journal_id = %(journal_id)s"""
        return (query, {'journal_id': self.id})

    def get_journal_dashboard_datas(self):
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        #add the number and sum of expenses to pay to the json defining the accounting dashboard data
        (query, query_args) = self._get_expenses_to_pay_query()
        self.env.cr.execute(query, query_args)
        query_results_to_pay = self.env.cr.dictfetchall()
        (number_to_pay, sum_to_pay) = self._count_results_and_sum_amounts(query_results_to_pay, self.company_id.currency_id)
        res['number_expenses_to_pay'] = number_to_pay
        res['sum_expenses_to_pay'] = formatLang(self.env, sum_to_pay or 0.0, currency_obj=self.currency_id or self.company_id.currency_id)
        return res

    def open_expenses_action(self):
        [action] = self.env.ref('hr_expense.action_hr_expense_sheet_all_all').read()
        action['context'] = {
            'search_default_approved': 1,
            'search_default_to_post': 1,
            'search_default_journal_id': self.id,
            'default_journal_id': self.id,
        }
        action['view_mode'] = 'tree,form'
        action['views'] = [(k,v) for k,v in action['views'] if v in ['tree', 'form']]
        return action

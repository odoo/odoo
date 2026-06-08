# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    category = fields.Selection(selection_add=[('expense', 'Expense')])
    billable_type = fields.Selection(selection_add=[('13_expense', 'Expenses')])

    def _set_billable_cost(self):
        aals_expense = self.filtered(lambda aal: aal.category == 'expense')
        aals_expense.billable_type = '13_expense'
        super(AccountAnalyticLine, self - aals_expense)._set_billable_cost()

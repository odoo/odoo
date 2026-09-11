# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    category = fields.Selection(selection_add=[('expense', 'Expense')])
    billable_type = fields.Selection(selection_add=[('12_expense_revenues', 'Expenses (Revenue)'),
                                                    ('22_expense', 'Expenses (Costs)')])

    @api.depends('billable_type')
    def _compute_category_report(self):
        expense_revenues = self.filtered(lambda aal: aal.billable_type == '12_expense_revenues')
        expense_revenues.category_report = 'revenues'
        super(AccountAnalyticLine, self - expense_revenues)._compute_category_report()

    def _set_billable_cost(self):
        aals_expense = self.filtered(lambda aal: aal.category == 'expense')
        aals_expense.billable_type = '22_expense'
        super(AccountAnalyticLine, self - aals_expense)._set_billable_cost()

    def _get_invoice_type(self, invoice_type):
        if self.category == 'expense':
            return '12_expense_revenues'
        return super()._get_invoice_type(invoice_type)

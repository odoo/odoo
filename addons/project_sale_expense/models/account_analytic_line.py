# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    category = fields.Selection(selection_add=[('expense', 'Expense')])

    def _get_billable_types(self):
        return super()._get_billable_types() + [
            (60, '18_expense_revenues', self.env._('Expenses (Revenue)')),
            (170, '13_expense', self.env._('Expenses (Costs)')),
        ]

    @api.depends('billable_type')
    def _compute_category_report(self):
        expense_revenues = self.filtered(lambda aal: aal.billable_type == '18_expense_revenues')
        expense_revenues.category_report = 'revenues'
        super(AccountAnalyticLine, self - expense_revenues)._compute_category_report()

    def _set_billable_cost(self):
        aals_expense = self.filtered(lambda aal: aal.category == 'expense')
        aals_expense.billable_type = '13_expense'
        super(AccountAnalyticLine, self - aals_expense)._set_billable_cost()

    @api.depends('so_line.is_expense')
    def _compute_project_billable_type(self):
        super()._compute_project_billable_type()

    def _get_invoice_type(self, invoice_type):
        if self.category == 'expense' or self.so_line.is_expense:
            return '18_expense_revenues'
        return super()._get_invoice_type(invoice_type)

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _hr_expense_get_general_info(self, expenses, payment_mode_str):
        company_currency = expenses.company_currency_id[:1]
        return {
            **super()._hr_expense_get_general_info(expenses, payment_mode_str),
            'untaxed_amount': company_currency.format(sum(expenses.mapped('untaxed_amount'), start=0)),
            'tax_amount': company_currency.format(sum(expenses.mapped('tax_amount'), start=0)),
        }

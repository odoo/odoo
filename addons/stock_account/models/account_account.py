from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_stock_variation_id = fields.Many2one(
        'account.account', string='Variation Account',
        help="At closing, register the inventory variation of the period into a specific account")
    account_stock_expense_id = fields.Many2one(
        'account.account', string='Expense Account',
        help="Counterpart used at closing for accounting adjustments to inventory valuation.")

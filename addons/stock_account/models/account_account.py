from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_stock_variation_id = fields.Many2one(
        'account.account', string='Variation Account',
        help="At closing, register the inventory variation of the period into a specific account")
    account_stock_expense_id = fields.Many2one(
        'account.account', string='Adjustment Account',
        help="Counter part used at closing for the book adjustments of the inventory valuation.")

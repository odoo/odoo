from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_stock_variation_id = fields.Many2one('account.account', string='Stock Variation')
    account_stock_expense_id = fields.Many2one('account.account', string='Expense')

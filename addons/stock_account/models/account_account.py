from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    account_stock_variation_id = fields.Many2one(
        comodel_name="account.account",
        string="Variation Account",
        domain=[
            (
                "account_type",
                "not in",
                (
                    "asset_receivable",
                    "liability_payable",
                    "asset_cash",
                    "liability_credit_card",
                ),
            )
        ],
        help="At closing, register the inventory variation of the period into a specific account",
    )
    account_stock_expense_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        domain=[
            (
                "account_type",
                "not in",
                (
                    "asset_receivable",
                    "liability_payable",
                    "asset_cash",
                    "liability_credit_card",
                ),
            )
        ],
        help="Counterpart used at closing for accounting adjustments to inventory valuation.",
    )

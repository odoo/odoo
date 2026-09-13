from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Account",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        ondelete="restrict",
        tracking=True,
        help="This account will be used when validating a customer invoice.",
    )
    property_account_expense_categ_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        ondelete="restrict",
        tracking=True,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.",
    )

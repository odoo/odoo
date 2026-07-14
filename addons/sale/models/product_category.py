from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_downpayment_categ_id = fields.Many2one(
        comodel_name='account.account',
        company_dependent=True,
        string="Downpayment Account",
        domain=[
            ('deprecated', '=', False),
            ('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))
        ],
        help="This account will be used on Downpayment invoices.",
        tracking=True,
    )

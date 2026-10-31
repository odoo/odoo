from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_stock_landed_costs = fields.Boolean("Landed Costs",
        help="Affect landed costs on reception operations and split them among products to update their cost price.")
    group_lot_on_invoice = fields.Boolean("Display Lots & Serial Numbers on Invoices",
        implied_group='stock_account.group_lot_on_invoice')

    valuation_account_id = fields.Many2one(
        'account.account',
        string='Cost of Production 1',
        related='company_id.valuation_account_id',
        readonly=False,
        domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))],
    )

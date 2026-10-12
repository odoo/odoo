# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_account_bills_to_receive_id = fields.Many2one(
        'account.account', 'Bills to Receive Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="Account holding the accrued value of the goods received but not billed yet. "
             "With perpetual valuation, it counterbalances the stock valuation account at closing.")
    property_account_bills_to_receive_active = fields.Boolean(
        related='property_account_bills_to_receive_id.active', string="Bills to Receive Account Active")
    property_account_billed_not_received_id = fields.Many2one(
        'account.account', 'Billed Not Received Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="Account holding the accrued value of the goods billed but not received yet. "
             "With perpetual valuation, it counterbalances the stock valuation account at closing.")
    property_account_billed_not_received_active = fields.Boolean(
        related='property_account_billed_not_received_id.active', string="Billed Not Received Account Active")

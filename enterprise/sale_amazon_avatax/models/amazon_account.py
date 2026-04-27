# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    def _create_order_from_data(self, order_data):
        """ Override to avoid recomputing taxes for orders made through Amazon. """
        order = super()._create_order_from_data(order_data)
        if order.fiscal_position_id.is_avatax:
            order.fiscal_position_id = False
        return order

    def _recompute_subtotal(self, subtotal, tax_amount, taxes, currency, _fiscal_pos=None):
        """ Override to not consider any tax and only use the tax_excluded amount from Amazon.

        This is done because Amazon does its own tax report to Avatax, but doesn't send the complete
        information to fill each individual separate tax. As when using Avatax, the tax report must
        be done within Avatax and not Odoo, we only include the tax excluded amount in the sale
        order line.
        """
        if not _fiscal_pos or not _fiscal_pos.is_avatax:
            return super()._recompute_subtotal(subtotal, tax_amount, taxes, currency, _fiscal_pos)
        return subtotal

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        # Override to prevent adding the avatax localisation for orders made through Amazon.
        # If there's no fiscal position on the order, the fiscal position of the partner is normally
        # used instead if any.
        values = super()._prepare_invoice()
        values_fp = self.env['account.fiscal.position'].browse(values['fiscal_position_id'])
        if self.amazon_order_ref and not self.fiscal_position_id and values_fp.is_avatax:
            values['fiscal_position_id'] = False
        return values

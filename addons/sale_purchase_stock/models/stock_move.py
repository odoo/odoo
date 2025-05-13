# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_description(self):
        # In a dropshipping context we do not need the description of the purchase order or it will be displayed
        # in Delivery slip report and it may be confusing for the customer to see several times the same text (product name + description_picking).
        if self.purchase_line_id and self.purchase_line_id.order_id.dest_address_id:
            product = self.product_id.with_context(lang=self.purchase_line_id.order_id.dest_address_id.lang or self.env.user.lang)
            return product._get_description(self.picking_type_id)
        return super()._get_description()

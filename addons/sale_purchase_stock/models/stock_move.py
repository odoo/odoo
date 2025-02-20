# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_incoming(self):
        """ Decides how a move's qty should count towards the received or delivered
        quantities of its generating purchase/sale order.
        """
        self.ensure_one()
        if self.purchase_line_id:
            location = self.location_id
            usage = 'supplier'
        elif self.sale_line_id:
            location = self.location_dest_id
            usage = 'customer'
        else:
            raise ValueError('_is_incoming() expects the stock move to have an order line.')
        return location.usage == usage or (location.usage == 'transit' and not location.company_id)

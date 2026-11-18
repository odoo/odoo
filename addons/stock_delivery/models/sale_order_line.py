# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_shipping_weight(self):
        # Packaging aware: the package type of the packaging adds its weight.
        self.ensure_one()
        return self.product_id._get_shipping_weight(self.product_uom_qty, self.product_uom_id)

    def _get_shipping_volume(self):
        # Packaging aware: the package type of the packaging gives the volume.
        self.ensure_one()
        return self.product_id._get_shipping_volume(self.product_uom_qty, self.product_uom_id)

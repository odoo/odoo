# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _remove_delivery_line(self):
        if self.carrier_id.delivery_type == 'onsite' and self.carrier_id.warehouse_id:
            self.env.add_to_compute(self._fields['partner_shipping_id'], self)
        super()._remove_delivery_line()

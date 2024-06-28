from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _set_delivery_method(self, *args, **kwargs):
        carrier_before = self.carrier_id
        fpos_before = self.fiscal_position_id
        super()._set_delivery_method(*args, **kwargs)
        if self.carrier_id.delivery_type == 'onsite' and self.carrier_id.warehouse_id:
            self.partner_shipping_id = self.carrier_id.warehouse_id.partner_id
        elif carrier_before.delivery_type == 'onsite':
            # setting partner_shipping_id as the carrier pickup location
            # overwrites the original partner shipping address
            # so it needs to be recomputed if the delivery method is not onsite picking
            self._compute_partner_shipping_id()
        if self.fiscal_position_id != fpos_before:
            self._recompute_taxes()

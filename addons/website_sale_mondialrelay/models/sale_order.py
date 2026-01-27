# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _is_cart_ready_for_payment(self, **kwargs):
        """Override of `website_sale` to check that Point Relais® is used with the correct delivery
        method, and vice versa."""
        ready = super()._is_cart_ready_for_payment(**kwargs)
        if not self._has_deliverable_products():
            return ready

        if (
            self.partner_shipping_id.is_mondialrelay
            and self.delivery_set
            and self.carrier_id
            and not self.carrier_id.is_mondialrelay
        ):
            self._add_alert(
                'danger', "Point Relais® can only be used with the delivery method Mondial Relay."
            )
            return False

        if not self.partner_shipping_id.is_mondialrelay and self.carrier_id.is_mondialrelay:
            self._add_alert(
                'danger', "Delivery method Mondial Relay can only ship to Point Relais®."
            )
            return False

        return ready

    def _compute_partner_shipping_id(self):
        super()._compute_partner_shipping_id()
        ecommerce_orders = self.filtered('website_id')
        for order in ecommerce_orders:
            if order.partner_shipping_id.is_mondialrelay and not order.carrier_id.is_mondialrelay:
                order.partner_shipping_id = order.partner_id

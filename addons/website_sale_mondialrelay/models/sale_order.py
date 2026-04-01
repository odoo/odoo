# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_cart_is_ready_to_be_paid(self):
        if (
            self.partner_shipping_id.is_mondialrelay and self.delivery_set
            and self.carrier_id and not self.carrier_id.is_mondialrelay
        ):
            raise ValidationError(_(
                "Point Relais® can only be used with the delivery method Mondial Relay."
            ))
        elif not self.partner_shipping_id.is_mondialrelay and self.carrier_id.is_mondialrelay:
            raise ValidationError(_(
                "Delivery method Mondial Relay can only ship to Point Relais®."
            ))
        return super()._check_cart_is_ready_to_be_paid()

    def _compute_partner_shipping_id(self):
        super()._compute_partner_shipping_id()
        ecommerce_orders = self.filtered('website_id')
        for order in ecommerce_orders:
            if order.partner_shipping_id.is_mondialrelay and not order.carrier_id.is_mondialrelay:
                order.partner_shipping_id = order.partner_id

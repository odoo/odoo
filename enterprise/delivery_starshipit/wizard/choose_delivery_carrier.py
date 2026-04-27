# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def create_new_starshipit_delivery_method(self):
        if self.delivery_type != 'starshipit':
            return

        order_vals = {
            'order_id': self.order_id.id,
            'carrier_id': self.carrier_id.id,
            'total_weight': self.total_weight,
            'destination_partner_id': self.order_id.partner_id.id,
        }
        return self.carrier_id.with_context(create_new_carrier=True, order_vals=order_vals).starshipit_action_load_shipping_carriers()

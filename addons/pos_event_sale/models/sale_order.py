# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def load_sale_order_from_pos(self, config_id):
        result = super().load_sale_order_from_pos(config_id)
        event_orders = self.filtered(lambda so: so.order_line.event_ticket_id)
        if not event_orders:
            return result
        order_with_registration = self.search([
            ("id", "in", self.ids),
            ("order_line.registration_ids.state", "!=", "cancel")
        ])
        order_with_registration_ids = set(order_with_registration.ids)
        for order_vals in result['sale.order']:
            order_vals['_has_event_registrations'] = order_vals['id'] in order_with_registration_ids
        return result

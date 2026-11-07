from collections import defaultdict

from odoo import models
from odoo.http import request


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    def _show_discount(self):
        """Determine if the discount should be shown on the website for this ticket."""
        self.ensure_one()
        if not self.price:
            return False

        product_sudo = self.product_id.sudo()
        pricelist = product_sudo.product_tmpl_id._get_contextual_pricelist()
        if not pricelist:
            return False

        rule_id = pricelist._get_product_rule(
            product=product_sudo,
            quantity=1.0,
        )
        pricelist_item = self.env['product.pricelist.item'].browse(rule_id)
        return pricelist_item._show_discount_on_shop() and (self.price - self.price_reduce) > 0

    def _get_current_limit_per_order(self, event_slot=False, event=False):
        """ Deduct the tickets already in the current cart from the limit. """
        limits = super()._get_current_limit_per_order(event_slot, event)
        for ticket_id, cart_quantity in self._get_cart_quantities(event_slot).items():
            limits[ticket_id] = max(0, limits[ticket_id] - cart_quantity)
        return limits

    def _get_cart_quantities(self, event_slot=False):
        """ Return the quantity of each ticket already in the current cart for the given slot. """
        order_sudo = request and getattr(request, 'cart', None)
        if not (self and order_sudo):
            return {}
        slot_id = event_slot.id if event_slot else False
        quantities = defaultdict(int)
        for line in order_sudo.order_line:
            if line.event_ticket_id in self and line.event_slot_id.id == slot_id:
                quantities[line.event_ticket_id.id] += int(line.product_uom_qty)
        return quantities

    def _is_order_limit_reached(self, event_slot=False):
        """ Whether the ticket is still on sale but the current cart already holds
        the maximum quantity allowed per order. """
        self.ensure_one()
        cart_quantity = self._get_cart_quantities(event_slot).get(self.id, 0)
        if not cart_quantity:
            return False
        limit_without_cart = super()._get_current_limit_per_order(event_slot)[self.id]
        return 0 < limit_without_cart <= cart_quantity

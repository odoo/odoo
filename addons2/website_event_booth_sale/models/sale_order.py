# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(
        self, product_id=None, line_id=None,
        event_booth_pending_ids=None, **kwargs
    ):
        """Check if there is another sale order line which already contains the requested event_booth_pending_ids
        to overwrite it with the newly requested booths to avoid having multiple so_line related to the same booths"""
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)

        if not event_booth_pending_ids or line_id:
            return lines

        return lines.filtered(
            lambda line: any(booth.id in event_booth_pending_ids for booth in line.event_booth_pending_ids)
        )

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """Forbid quantity updates on event booth lines."""
        product = self.env['product.product'].browse(product_id)
        if product.detailed_type == 'event_booth' and new_qty > 1:
            return 1, _('You cannot manually change the quantity of an Event Booth product.')
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _prepare_order_line_values(
        self, product_id, quantity, event_booth_pending_ids=False, registration_values=None,
        **kwargs
    ):
        """Add corresponding event to the SOline creation values (if booths are provided)."""
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)

        if not event_booth_pending_ids:
            return values

        booths = self.env['event.booth'].browse(event_booth_pending_ids)

        values['event_id'] = booths.event_id.id
        values['event_booth_registration_ids'] = [
            Command.create({
                'event_booth_id': booth.id,
                **registration_values,
            }) for booth in booths
        ]

        return values

    # FIXME VFE investigate if it ever happens.
    # Probably not
    def _prepare_order_line_update_values(
        self, order_line, quantity, event_booth_pending_ids=False, registration_values=None,
        **kwargs
    ):
        """Delete existing booth registrations and create new ones with the update values."""
        values = super()._prepare_order_line_update_values(order_line, quantity, **kwargs)

        if not event_booth_pending_ids:
            return values

        booths = self.env['event.booth'].browse(event_booth_pending_ids)
        values['event_booth_registration_ids'] = [
            Command.delete(registration.id)
            for registration in order_line.event_booth_registration_ids
        ] + [
            Command.create({
                'event_booth_id': booth.id,
                **registration_values,
            }) for booth in booths
        ]

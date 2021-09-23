# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        """Check if there is another sale order line which already contains the requested event_booth_pending_ids
        to overwrite it with the newly requested booths to avoid having multiple so_line related to the same booths"""
        self.ensure_one()
        lines = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return lines
        event_booth_pending_ids = kwargs.get('event_booth_pending_ids')
        if event_booth_pending_ids:
            lines = lines.filtered(
                lambda line: any(booth.id in event_booth_pending_ids for booth in line.event_booth_pending_ids)
            )
        return lines

    def _website_product_id_change(self, order_id, product_id, qty=0, **kwargs):
        values = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty, **kwargs)
        event_booth_pending_ids = kwargs.get('event_booth_pending_ids')
        if event_booth_pending_ids:
            order_line = self.env['sale.order.line'].sudo().search([
                ('id', 'in', self.order_line.ids),
                ('event_booth_pending_ids', 'in', event_booth_pending_ids)])
            booths = self.env['event.booth'].browse(event_booth_pending_ids)
            new_registration_ids = [Command.create({
                                        'event_booth_id': booth.id,
                                        **kwargs.get('registration_values'),
                                    }) for booth in booths]
            if order_line:
                event_booth_registration_ids = [Command.delete(reg.id)
                                                for reg in order_line.event_booth_registration_ids] + new_registration_ids
            else:
                event_booth_registration_ids = new_registration_ids

            values.update(
                event_id=booths.event_id.id,
                event_booth_registration_ids=event_booth_registration_ids,
                name=booths._get_booth_multiline_description,
            )

        return values

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = {}
        product = self.env['product.product'].browse(product_id)
        if product.detailed_type == 'event_booth' and set_qty > 1:
            set_qty = 1
            values['warning'] = _('You cannot manually change the quantity of an Event Booth product.')
        values.update(super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs))
        return values

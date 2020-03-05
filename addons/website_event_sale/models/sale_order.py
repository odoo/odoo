# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_line_values(self, product, qty, **kwargs):
        values = super(SaleOrder, self)._prepare_line_values(product, qty, **kwargs)
        event_ticket_id = None

        if self.env.context.get("event_ticket_id"):
            event_ticket_id = self.env.context.get("event_ticket_id")
        else:
            if product.event_ticket_ids:
                event_ticket_id = product.event_ticket_ids[0].id

        if event_ticket_id:
            ticket = self.env['event.event.ticket'].browse(event_ticket_id)
            if product != ticket.product_id:
                raise UserError(_("The ticket doesn't match with this product."))

            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id

            values['name'] = ticket._get_ticket_multiline_description()

        # avoid writing related values that end up locking the product record
        values.pop('event_ok', None)

        return values

    def _check_quantity(self, product, old_qty, new_qty, line=None):
        new_qty, warning = super(SaleOrder, self)._check_quantity(product, old_qty, new_qty, line)
        ticket = self.env['event.event.ticket']

        if line:
            ticket = line.event_ticket_id
        elif product.event_ok:
            # product.event_ticket_ids ?
            ticket = ticket.search([('product_id', '=', product.id)], limit=1)

        if not ticket:
            return new_qty, warning

        # Reserved seats are counted as unavailable
        requested_qty = new_qty - old_qty
        if old_qty < new_qty:
            # case: buying tickets for a sold out ticket
            if ticket and ticket.seats_availability == 'limited' and ticket.seats_available <= 0:
                warning = _('Sorry, The %(ticket)s tickets for the %(event)s event are sold out.') % {
                    'ticket': ticket.name,
                    'event': ticket.event_id.name
                }
                new_qty = old_qty
            # case: buying tickets, too much attendees
            elif ticket and ticket.seats_availability == 'limited' and requested_qty > ticket.seats_available:
                warning = _('Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event.') % {
                    'remaining_seats': ticket.seats_available,
                    'ticket': ticket.name,
                    'event': ticket.event_id.name
                }
                new_qty = old_qty + ticket.seats_available

        return new_qty, warning


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_id.display_name', 'event_ticket_id.display_name')
    def _compute_name_short(self):
        """ If the sale order line concerns a ticket, we don't want the product name, but the ticket name instead.
        """
        super(SaleOrderLine, self)._compute_name_short()

        for record in self:
            if record.event_ticket_id:
                record.name_short = record.event_ticket_id.display_name

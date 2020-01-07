# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        lines = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return lines
        domain = [('id', 'in', lines.ids)]
        if self.env.context.get("event_ticket_id"):
            domain.append(('event_ticket_id', '=', self.env.context.get("event_ticket_id")))
        return self.env['sale.order.line'].sudo().search(domain)

    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.env['sale.order'].sudo().browse(order_id)
        if self._context.get('pricelist') != order.pricelist_id.id:
            self = self.with_context(pricelist=order.pricelist_id.id)

        values = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty)
        event_ticket_id = None
        if self.env.context.get("event_ticket_id"):
            event_ticket_id = self.env.context.get("event_ticket_id")
        else:
            product = self.env['product.product'].browse(product_id)
            if product.event_ticket_ids:
                event_ticket_id = product.event_ticket_ids[0].id

        if event_ticket_id:
            ticket = self.env['event.event.ticket'].browse(event_ticket_id)
            if product_id != ticket.product_id.id:
                raise UserError(_("The ticket doesn't match with this product."))

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            if order.pricelist_id.discount_policy == 'without_discount':
                values['price_unit'] = ticket.price
            else:
                values['price_unit'] = ticket.price_reduce
            values['name'] = ticket.get_ticket_multiline_description_sale()

        # avoid writing related values that end up locking the product record
        values.pop('event_ok', None)

        return values

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        OrderLine = self.env['sale.order.line']

        if line_id:
            line = OrderLine.browse(line_id)
            ticket = line.event_ticket_id
            old_qty = int(line.product_uom_qty)
            if ticket.id:
                self = self.with_context(event_ticket_id=ticket.id, fixed_price=1)
        else:
            line = None
            ticket = self.env['event.event.ticket'].search([('product_id', '=', product_id)], limit=1)
            old_qty = 0
        new_qty = set_qty if set_qty else (add_qty or 0 + old_qty)

        # case: buying tickets for a sold out ticket
        values = {}
        if ticket and ticket.seats_availability == 'limited' and ticket.seats_available <= 0:
            values['warning'] = _('Sorry, The %(ticket)s tickets for the %(event)s event are sold out.') % {
                'ticket': ticket.name,
                'event': ticket.event_id.name}
            new_qty, set_qty, add_qty = 0, 0, -old_qty
        # case: buying tickets, too much attendees
        elif ticket and ticket.seats_availability == 'limited' and new_qty > ticket.seats_available:
            values['warning'] = _('Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event.') % {
                'remaining_seats': ticket.seats_available,
                'ticket': ticket.name,
                'event': ticket.event_id.name}
            new_qty, set_qty, add_qty = ticket.seats_available, ticket.seats_available, 0
        values.update(super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs))

        # removing attendees
        if ticket and new_qty < old_qty:
            attendees = self.env['event.registration'].search([
                ('state', '!=', 'cancel'),
                ('sale_order_id', 'in', self.ids),  # To avoid break on multi record set
                ('event_ticket_id', '=', ticket.id),
            ], offset=new_qty, limit=(old_qty - new_qty), order='create_date asc')
            attendees.button_reg_cancel()
        # adding attendees
        elif ticket and new_qty > old_qty:
            line = OrderLine.browse(values['line_id'])
            line._update_registrations(confirm=False, cancel_to_draft=True, registration_data=kwargs.get('registration_data', []))
            # add in return values the registrations, to display them on website (or not)
            values['attendee_ids'] = self.env['event.registration'].search([('sale_order_line_id', '=', line.id), ('state', '!=', 'cancel')]).ids
        return values


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

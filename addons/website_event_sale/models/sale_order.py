# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, product_id, event_ticket_id=False, **kwargs):
        lines = super()._cart_find_product_line(
            product_id, event_ticket_id=event_ticket_id, **kwargs,
        )
        if not event_ticket_id:
            return lines

        return lines.filtered(lambda line: line.event_ticket_id.id == event_ticket_id)

    def _verify_updated_quantity(self, order_line, product_id, new_qty, event_ticket_id=False, **kwargs):
        """Restrict quantity updates for event tickets according to available seats."""
        new_qty, warning = super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

        if not event_ticket_id:
            if not order_line.event_ticket_id or new_qty < order_line.product_uom_qty:
                return new_qty, warning
            else:
                return order_line.product_uom_qty, _("You cannot raise manually the event ticket quantity in your cart")

        # Adding new ticket to the cart (might be automatically linked to an existing line)
        if kwargs.get('slot_id'):
            ticket = self.env['event.slot.ticket'].search([('slot_id', '=', kwargs['slot_id']), ('ticket_id', '=', event_ticket_id)]).exists()
            ticket_seats_limited = ticket.ticket_id.seats_limited
        else:
            ticket = self.env['event.event.ticket'].browse(event_ticket_id).exists()
            ticket_seats_limited = ticket.seats_limited
        if not ticket:
            raise UserError(_("The provided ticket doesn't exist"))

        # TODO TDE consider full cart qty and not only added qty
        # if event seats are not auto confirmed.
        # Since created registrations are automatically reserved
        # We should only consider new added qty and not full quantity
        # when checking for seat availability
        existing_qty = order_line.product_uom_qty if order_line else 0
        qty_added = new_qty - existing_qty
        warning = ''
        if ticket_seats_limited and ticket.seats_available <= 0:
            # Remove existing line if exists and do not add a new one
            # if no ticket is available anymore
            new_qty = existing_qty
            warning = _(
                'Sorry, The %(ticket)s tickets for the %(event)s event are sold out.',
                ticket=ticket.name,
                event=ticket.event_id.name,
            )
        elif ticket_seats_limited and qty_added > ticket.seats_available:
            new_qty = existing_qty + ticket.seats_available
            warning = _(
                'Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event.',
                remaining_seats=ticket.seats_available,
                ticket=ticket.name,
                event=ticket.event_id.name,
            )

        return new_qty, warning

    def _prepare_order_line_values(self, product_id, quantity, event_ticket_id=False, **kwargs):
        """Add corresponding event to the SOline creation values (if ticket is provided)."""
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)

        if not event_ticket_id:
            return values

        ticket = self.env['event.event.ticket'].browse(event_ticket_id)

        if ticket.product_id.id != product_id:
            raise UserError(_("The ticket doesn't match with this product."))

        values['event_id'] = ticket.event_id.id
        values['event_ticket_id'] = ticket.id

        return values

    def _cart_update_order_line(self, order_line, quantity, **kwargs):
        old_qty = order_line.product_uom_qty

        updated_line = super()._cart_update_order_line(order_line, quantity, **kwargs)

        # Remove event registrations on quantity decrease.
        if (
            updated_line
            and updated_line.event_ticket_id
            and (diff := old_qty - updated_line.product_uom_qty) > 0
        ):
            attendees = self.env['event.registration'].search(
                domain=[
                    ('state', '!=', 'cancel'),
                    ('sale_order_id', '=', self.id),
                    ('event_ticket_id', '=', order_line.event_ticket_id.id),
                ],
                offset=updated_line.product_uom_qty,
                limit=diff,
                order='create_date asc',
            )
            attendees.action_cancel()

        return updated_line


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

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, *args, event_slot_id=False, event_ticket_id=False, **kwargs):
        lines = super()._cart_find_product_line(
            *args, event_slot_id=event_slot_id, event_ticket_id=event_ticket_id, **kwargs,
        )
        if not event_slot_id and not event_ticket_id:
            return lines

        return lines.filtered(lambda line: line.event_slot_id.id == event_slot_id and line.event_ticket_id.id == event_ticket_id)

    def _verify_updated_quantity(
        self, order_line, product_id, new_qty, uom_id, *, event_slot_id=False, event_ticket_id=False, **kwargs
    ):
        """Restrict quantity updates for event tickets according to available seats."""
        new_qty, warning = super()._verify_updated_quantity(
            order_line,
            product_id,
            new_qty,
            uom_id,
            event_slot_id=event_slot_id,
            event_ticket_id=event_ticket_id,
            **kwargs,
        )

        if (
            order_line.is_event_ticket_option
            and not self.env.context.get('event_ticket_option_sync')
            and new_qty > order_line.product_uom_qty
        ):
            # option quantities follow the attendees' choices
            return order_line.product_uom_qty, _(
                "Options are chosen per attendee: register a new attendee to add this option again.",
            )

        if not event_ticket_id:
            if not order_line.event_ticket_id or new_qty < order_line.product_uom_qty:
                return new_qty, warning
            else:
                return order_line.product_uom_qty, _("You cannot raise manually the event ticket quantity in your cart")

        # Adding new ticket to the cart (might be automatically linked to an existing line)
        ticket = self.env['event.event.ticket'].browse(event_ticket_id).exists()
        if not ticket:
            raise UserError(_("The provided ticket doesn't exist"))
        slot = self.env['event.slot'].browse(event_slot_id).exists()
        if event_slot_id and not slot:
            raise UserError(_("The provided ticket slot doesn't exist"))

        # TODO TDE consider full cart qty and not only added qty
        # if event seats are not auto confirmed.
        # Since created registrations are automatically reserved
        # We should only consider new added qty and not full quantity
        # when checking for seat availability
        existing_qty = order_line.product_uom_qty if order_line else 0
        qty_added = new_qty - existing_qty
        warning = ''
        ticket_seats_available = ticket.event_id._get_seats_availability([(slot, ticket)])[0] if slot else ticket.seats_available
        if ticket.seats_limited and ticket_seats_available is not None and ticket_seats_available <= 0:
            # Remove existing line if exists and do not add a new one
            # if no ticket is available anymore
            new_qty = existing_qty
            warning = _(
                'Sorry, The %(ticket)s tickets for the %(event)s event are sold out.',
                ticket=ticket.name,
                event=ticket.event_id.name,
            )
        elif ticket.seats_limited and ticket_seats_available is not None and qty_added > ticket_seats_available:
            new_qty = existing_qty + ticket_seats_available
            warning = _(
                'Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event%(slot)s.',
                remaining_seats=ticket_seats_available,
                slot=f' on {slot.name}' if slot else '',
                ticket=ticket.name,
                event=ticket.event_id.name,
            )

        return new_qty, warning

    def _prepare_order_line_values(self, product_id, *args, event_slot_id=False, event_ticket_id=False, **kwargs):
        """Add corresponding event to the SOline creation values (if ticket is provided)."""
        values = super()._prepare_order_line_values(
            product_id, *args, event_ticket_id=event_ticket_id, **kwargs,
        )

        if not event_ticket_id:
            return values

        ticket = self.env['event.event.ticket'].browse(event_ticket_id)

        if ticket.product_id.id != product_id:
            raise UserError(_("The ticket doesn't match with this product."))

        values['event_id'] = ticket.event_id.id
        values['event_ticket_id'] = ticket.id
        values['event_slot_id'] = event_slot_id

        return values

    def _cart_update_order_line(self, order_line, quantity, **kwargs):
        old_qty = order_line.product_uom_qty
        was_option = order_line.is_event_ticket_option
        ticket_line = order_line.linked_line_id if was_option else order_line
        product = order_line.product_id

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
                    ('event_slot_id', '=', order_line.event_slot_id.id),
                    ('event_ticket_id', '=', order_line.event_ticket_id.id),
                ],
                offset=updated_line.product_uom_qty,
                limit=diff,
                order='create_date asc',
            )
            attendees.action_cancel()

        if self.env.context.get('event_ticket_option_sync'):
            return updated_line

        if was_option and ticket_line.exists():
            # Option lowered or removed in the cart: drop it from the attendees who registered
            # last, so that registrations and order stay consistent.
            remaining = int(updated_line.product_uom_qty) if updated_line else 0
            holders = self._get_event_ticket_option_registrations(ticket_line).filtered(
                lambda registration: product in registration.ticket_option_product_ids,
            )
            holders[remaining:].with_context(event_ticket_option_sync=True).write({
                'ticket_option_product_ids': [Command.unlink(product.id)],
            })

        return updated_line

    def _create_event_ticket_option_line(self, ticket_line, product, quantity):
        """ Override of `event_sale` to add the option to website carts like any cart line. """
        if not self.website_id:
            return super()._create_event_ticket_option_line(ticket_line, product, quantity)
        values = self.with_context(event_ticket_option_sync=True)._cart_add(
            product_id=product.id, quantity=quantity, linked_line_id=ticket_line.id,
        )
        line = self.env['sale.order.line'].browse(values['line_id'])
        line.is_event_ticket_option = True
        return line

    def _filter_can_send_abandoned_cart_followup(self):
        # Prevent carts with expired/sold out tickets from being subject of reminder emails
        return super()._filter_can_send_abandoned_cart_followup().filtered(
            lambda so: all(ticket.sale_available for ticket in so.order_line.event_ticket_id),
        )

    def _needs_customer_address(self):
        """Override of `website_sale` to avoid requesting full address details for event
        registrations."""
        res = super()._needs_customer_address()

        # service options are part of the registration; goods ones need the address to be delivered
        if self.order_line and all(
            line.event_ticket_id or (line.is_event_ticket_option and line.product_id.type == "service")
            for line in self.order_line
        ):
            return self.env["ir.config_parameter"].sudo().get_bool(
                    "website_event_sale.require_billing_details_for_events"
            )

        return res

    def _is_cart_ready_for_checkout(self):
        """Override of `website_sale` to check if the user is trying to order a ticket that is no
        longer available."""
        ready = super()._is_cart_ready_for_checkout()
        if not self.order_line.event_id:
            return ready

        # Check that there are enough seats available per ticket.
        registration_domain = [
            ('sale_order_id', '=', self.id),
            ('event_ticket_id', '!=', False),
            ('state', '!=', 'cancel'),
        ]
        registrations_per_event = self.env['event.registration'].sudo()._read_group(
            registration_domain,
            ['event_id'], ['id:recordset']
        )
        for event, registrations in registrations_per_event:
            count_per_slot_ticket = self.env['event.registration'].sudo()._read_group(
                [('id', 'in', registrations.ids)],
                ['event_slot_id', 'event_ticket_id'], ['__count']
            )
            try:
                event._verify_seats_availability(count_per_slot_ticket)
            except ValidationError as exc:
                self._add_blocking_alert(str(exc))
                # Displayed in a little sign next to the order line.
                registrations.sale_order_line_id._add_warning_alert(str(exc))
                ready = False

        return ready

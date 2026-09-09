from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(
        self, *args, event_slot_id=False, event_ticket_id=False, **kwargs
    ):
        lines = super()._cart_find_product_line(
            *args,
            event_slot_id=event_slot_id,
            event_ticket_id=event_ticket_id,
            **kwargs,
        )
        if not event_slot_id and not event_ticket_id:
            return lines

        return lines.filtered(
            lambda line: (
                line.event_slot_id.id == event_slot_id
                and line.event_ticket_id.id == event_ticket_id
            )
        )

    def _get_updated_quantity(
        self,
        order_line,
        product_id,
        new_qty,
        uom_id,
        *,
        event_slot_id=False,
        event_ticket_id=False,
        **kwargs,
    ):
        new_qty, warning = super()._get_updated_quantity(
            order_line,
            product_id,
            new_qty,
            uom_id,
            event_slot_id=event_slot_id,
            event_ticket_id=event_ticket_id,
            **kwargs,
        )

        if not event_ticket_id:
            if not order_line.event_ticket_id or new_qty < order_line.product_uom_qty:
                return new_qty, warning
            else:
                _debug.logic(
                    "ticket_quantity_raise_refused",
                    line=order_line,
                    ticket=order_line.event_ticket_id,
                    requested=new_qty,
                    kept=order_line.product_uom_qty,
                )
                return order_line.product_uom_qty, _(
                    "You cannot raise manually the event ticket quantity in your cart"
                )

        ticket = self.env["event.event.ticket"].browse(event_ticket_id).exists()
        if not ticket:
            raise UserError(_("The provided ticket doesn't exist"))
        slot = self.env["event.slot"].browse(event_slot_id).exists()
        if event_slot_id and not slot:
            raise UserError(_("The provided ticket slot doesn't exist"))

        existing_qty = order_line.product_uom_qty if order_line else 0
        qty_added = new_qty - existing_qty
        warning = ""
        # Always go through the helper: it combines the event (or slot) cap with
        # the ticket cap, whereas `ticket.seats_available` only knows about the
        # ticket and ignores a capped event selling an uncapped ticket. `None`
        # is the helper's documented "no limit" sentinel.
        seats_available = ticket.event_id._get_seats_availability([(slot, ticket)])[0]
        if seats_available is not None and qty_added > 0 and seats_available <= 0:
            _debug.logic(
                "ticket_sold_out",
                ticket=ticket,
                event=ticket.event_id,
                slot=slot,
                requested=new_qty,
                kept=existing_qty,
            )
            # Keep the existing line's quantity unchanged, and do not create a
            # new line, if no ticket is available anymore
            new_qty = existing_qty
            warning = _(
                "Sorry, The %(ticket)s tickets for the %(event)s event are sold out.",
                ticket=ticket.name,
                event=ticket.event_id.name,
            )
        elif seats_available is not None and qty_added > seats_available:
            _debug.logic(
                "ticket_quantity_clamped",
                ticket=ticket,
                event=ticket.event_id,
                slot=slot,
                requested=new_qty,
                available=seats_available,
                kept=existing_qty + seats_available,
            )
            new_qty = existing_qty + seats_available
            warning = _(
                "Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event%(slot)s.",
                remaining_seats=seats_available,
                slot=f" on {slot.name}" if slot else "",
                ticket=ticket.name,
                event=ticket.event_id.name,
            )

        return new_qty, warning

    def _prepare_order_line_values(
        self, product_id, *args, event_slot_id=False, event_ticket_id=False, **kwargs
    ):
        values = super()._prepare_order_line_values(
            product_id,
            *args,
            event_ticket_id=event_ticket_id,
            **kwargs,
        )

        if not event_ticket_id:
            return values

        ticket = self.env["event.event.ticket"].browse(event_ticket_id).exists()
        if not ticket:
            raise UserError(_("The provided ticket doesn't exist"))

        if ticket.product_id.id != product_id:
            raise UserError(_("The ticket doesn't match with this product."))

        values["event_id"] = ticket.event_id.id
        values["event_ticket_id"] = ticket.id
        values["event_slot_id"] = event_slot_id
        _debug.pipeline(
            "ticket_line_values",
            ticket=ticket,
            event=ticket.event_id,
            slot=event_slot_id,
        )

        return values

    def _cart_update_order_line(self, order_line, quantity, **kwargs):
        old_qty = order_line.product_uom_qty

        updated_line = super()._cart_update_order_line(order_line, quantity, **kwargs)

        if (
            updated_line
            and updated_line.event_ticket_id
            and (diff := old_qty - updated_line.product_uom_qty) > 0
        ):
            attendees = self.env["event.registration"].search(
                domain=[
                    ("state", "!=", "cancel"),
                    ("sale_order_id", "=", self.id),
                    ("event_slot_id", "=", order_line.event_slot_id.id),
                    ("event_ticket_id", "=", order_line.event_ticket_id.id),
                ],
                offset=updated_line.product_uom_qty,
                limit=diff,
                order="create_date asc",
            )
            _debug.lifecycle(
                "attendees_cancelled_on_quantity_drop",
                order=self,
                line=updated_line,
                ticket=updated_line.event_ticket_id,
                removed=diff,
                attendees=attendees,
            )
            attendees.action_cancel()

        return updated_line

    def _filter_can_send_abandoned_cart_mail(self):
        return (
            super()
            ._filter_can_send_abandoned_cart_mail()
            .filtered(
                lambda so: all(
                    ticket.sale_available for ticket in so.line_ids.event_ticket_id
                ),
            )
        )

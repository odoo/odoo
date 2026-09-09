from collections import defaultdict

from odoo import Command
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_event.controllers.main import WebsiteEventController

_debug = DebugLog(__name__)


class WebsiteEventSaleController(WebsiteEventController):
    def _process_tickets_form(self, event, form_details):
        res = super()._process_tickets_form(event, form_details)
        for item in res:
            item["price"] = item["ticket"]["price"] if item["ticket"] else 0
        return res

    def _create_attendees_from_registration_post(self, event, registration_data):
        # `registration_confirm` below needs this very list, which the parent
        # has already parsed out of the POST. Stash it on `request`, which is
        # per-request state: controllers are instantiated once per registry
        # (odoo/http/routing.py), so caching it on `self` would leak one
        # visitor's names, emails and phone numbers into another's request.
        request.website_event_sale_registrations = registration_data

        if not any(info.get("event_ticket_id") for info in registration_data):
            _debug.logic(
                "attendees_without_tickets",
                event=event,
                registrations=len(registration_data),
            )
            return super()._create_attendees_from_registration_post(
                event, registration_data
            )

        event_ticket_ids = [
            registration["event_ticket_id"]
            for registration in registration_data
            if registration.get("event_ticket_id")
        ]
        event_ticket_by_id = {
            event_ticket.id: event_ticket
            for event_ticket in request.env["event.event.ticket"]
            .sudo()
            .browse(event_ticket_ids)
        }

        if (
            all(event_ticket.price == 0 for event_ticket in event_ticket_by_id.values())
            and not request.cart.id
        ):
            _debug.logic(
                "free_tickets_no_cart",
                event=event,
                tickets=len(event_ticket_by_id),
                registrations=len(registration_data),
            )
            return super()._create_attendees_from_registration_post(
                event, registration_data
            )

        order_sudo = request.cart or request.website._create_cart()
        tickets_data = defaultdict(int)
        for data in registration_data:
            event_slot_id = data.get("event_slot_id", False)
            event_ticket_id = data.get("event_ticket_id", False)
            if event_ticket_id:
                tickets_data[event_slot_id, event_ticket_id] += 1

        cart_data = {}
        for (slot_id, ticket_id), count in tickets_data.items():
            ticket_sudo = event_ticket_by_id.get(ticket_id)
            cart_values = order_sudo._cart_add(
                product_id=ticket_sudo.product_id.id,
                quantity=count,
                event_ticket_id=ticket_id,
                event_slot_id=slot_id,
            )
            cart_data[slot_id, ticket_id] = cart_values["line_id"]
            _debug.lifecycle(
                "ticket_added_to_cart",
                order=order_sudo,
                ticket=ticket_sudo,
                slot=slot_id,
                quantity=count,
                line=cart_values["line_id"],
            )

        for data in registration_data:
            event_slot_id = data.get("event_slot_id", False)
            event_ticket_id = data.get("event_ticket_id", False)
            event_ticket = event_ticket_by_id.get(event_ticket_id)
            if event_ticket:
                data["sale_order_id"] = order_sudo.id
                data["sale_order_line_id"] = cart_data[event_slot_id, event_ticket_id]

        return super()._create_attendees_from_registration_post(
            event, registration_data
        )

    def _registration_address_values(self, registration_values):
        values = dict(registration_values)
        commands = values.pop("phone_ids", None)
        for command in commands or ():
            if command[0] == Command.CREATE and command[2].get("number"):
                values["phone"] = command[2]["number"]
                break
        return values

    @route()
    def registration_confirm(self, event, **post):
        request.website_event_sale_registrations = None
        res = super().registration_confirm(event, **post)

        # Reuse the parse `_create_attendees_from_registration_post` stashed
        # instead of running `_process_attendees_form` on the same POST a
        # second time: it re-validates every posted ticket and slot id and
        # re-parses every attendee field and answer. The stash is absent when
        # the parent redirected before creating any attendee, and we then
        # parse as before rather than change what those paths answer.
        registrations = request.website_event_sale_registrations
        if registrations is None:
            registrations = self._process_attendees_form(event, post)
        order_sudo = request.cart
        if not any(line.event_ticket_id for line in order_sudo.line_ids):
            _debug.logic("confirm_without_ticket_lines", event=event, order=order_sudo)
            return res

        if any(info["event_ticket_id"] for info in registrations):
            _debug.pipeline(
                "registration_confirm",
                event=event,
                order=order_sudo,
                amount_total=order_sudo.amount_total,
                registrations=len(registrations),
                anonymous=order_sudo._is_anonymous_cart(),
            )
            if order_sudo.amount_total:
                if order_sudo._is_anonymous_cart():
                    booked_by_partner, feedback_dict = (
                        CustomerPortal()._create_or_update_address(
                            request.env["res.partner"].sudo(),
                            order_sudo=order_sudo,
                            verify_address_values=False,
                            **self._registration_address_values(registrations[0]),
                        )
                    )
                    _debug.logic(
                        "anonymous_cart_address",
                        order=order_sudo,
                        partner=booked_by_partner,
                        invalid_fields=feedback_dict.get("invalid_fields") or (),
                    )
                    if not feedback_dict.get("invalid_fields"):
                        order_sudo._update_address(booked_by_partner.id, ["partner_id"])
                request.session["sale_last_order_id"] = order_sudo.id
                return request.redirect("/shop/checkout?try_skip_step=true")
            else:
                _debug.lifecycle("free_order_confirmed", order=order_sudo, event=event)
                order_sudo.action_confirm()
                request.website.sale_reset()
                request.session["sale_last_order_id"] = order_sudo.id
                return request.redirect("/shop/confirmation")

        return res

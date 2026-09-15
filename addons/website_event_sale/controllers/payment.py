from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale.controllers.payment import PaymentPortal

_debug = DebugLog(__name__)


class PaymentPortalOnsite(PaymentPortal):
    def _check_transaction_for_order(self, transaction, sale_order):
        super()._check_transaction_for_order(transaction, sale_order)
        registration_domain = [
            ("sale_order_id", "=", sale_order.id),
            ("event_ticket_id", "!=", False),
            ("state", "!=", "cancel"),
        ]
        registrations_per_event = (
            request.env["event.registration"]
            .sudo()
            ._read_group(registration_domain, ["event_id"], ["id:recordset"])
        )
        for event, registrations in registrations_per_event:
            count_per_slot_ticket = (
                request.env["event.registration"]  # noqa: E8507 - one aggregate per event of the cart
                .sudo()
                ._read_group(
                    [("id", "in", registrations.ids)],
                    ["event_slot_id", "event_ticket_id"],
                    ["__count"],
                )
            )
            _debug.pipeline(
                "seats_checked_before_payment",
                order=sale_order,
                event=event,
                registrations=registrations,
                groups=len(count_per_slot_ticket),
            )
            event._check_seats_availability(
                [(slot, ticket, count) for slot, ticket, count in count_per_slot_ticket]
            )

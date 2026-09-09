from collections import defaultdict

from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale.controllers.payment import PaymentPortal

_debug = DebugLog(__name__)


class PaymentPortalOnsite(PaymentPortal):
    def _check_transaction_for_order(self, transaction, sale_order):
        """
        Throws a ValidationError if the user tries to pay for a ticket which isn't available
        """
        super()._check_transaction_for_order(transaction, sale_order)
        # Only the registrations still waiting for a seat are checked. The
        # `open` and `done` ones are already counted as taken by
        # `_get_seats_availability`, so counting them here too would demand
        # seats the order itself already holds and reject the payment.
        registration_domain = [
            ("sale_order_id", "=", sale_order.id),
            ("event_ticket_id", "!=", False),
            ("state", "=", "draft"),
        ]
        counts_per_event = defaultdict(list)
        registration_counts = (
            request.env["event.registration"]
            .sudo()
            ._read_group(
                registration_domain,
                ["event_id", "event_slot_id", "event_ticket_id"],
                ["__count"],
            )
        )
        for event, slot, ticket, count in registration_counts:
            counts_per_event[event].append((slot, ticket, count))
        for event, slot_ticket_counts in counts_per_event.items():
            _debug.pipeline(
                "seats_checked_before_payment",
                order=sale_order,
                event=event,
                groups=len(slot_ticket_counts),
            )
            event._check_seats_availability(slot_ticket_counts)

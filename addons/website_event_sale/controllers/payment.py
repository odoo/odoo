from odoo.http import request
from odoo.addons.website_sale.controllers.payment import PaymentPortal


class PaymentPortalOnsite(PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order):
        """
        Throws a ValidationError if the user tries to pay for a ticket which isn't available
        """
        super()._validate_transaction_for_order(transaction, sale_order)
        registration_domain = [
            ('sale_order_id', '=', sale_order.id),
            ('event_ticket_id', '!=', False),
            ('state', '!=', 'cancel'),
        ]
        count_per_ticket = request.env['event.registration'].sudo()._read_group(
            registration_domain,
            ['event_ticket_id'], ['__count']
        )
        for ticket, count in count_per_ticket:
            ticket._check_seats_availability(minimal_availability=count)

        count_per_event = request.env['event.registration'].sudo()._read_group(
            registration_domain,
            ['event_id'], ['__count']
        )
        for event, count in count_per_event:
            event._check_seats_availability(minimal_availability=count)

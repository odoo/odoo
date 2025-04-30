# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        registrations_per_event = request.env['event.registration'].sudo()._read_group(
            registration_domain,
            ['event_id'], ['id:recordset']
        )
        for event, registrations in registrations_per_event:
            count_per_slot_ticket = request.env['event.registration'].sudo()._read_group(
                [('id', 'in', registrations.ids)],
                ['event_slot_id', 'event_ticket_id'], ['__count']
            )
            event._verify_seats_availability([
                (slot, ticket, count)
                for slot, ticket, count in count_per_slot_ticket
            ])

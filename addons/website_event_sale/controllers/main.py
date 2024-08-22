# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo.http import request, route

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventSaleController(WebsiteEventController):

    def _process_tickets_form(self, event, form_details):
        """ Add price information on ticket order """
        res = super()._process_tickets_form(event, form_details)
        for item in res:
            item['price'] = item['ticket']['price'] if item['ticket'] else 0
        return res

    def _create_attendees_from_registration_post(self, event, registration_data):
        # we have at least one registration linked to a ticket -> sale mode activate
        if not any(info.get('event_ticket_id') for info in registration_data):
            return super()._create_attendees_from_registration_post(event, registration_data)

        event_ticket_ids = [registration['event_ticket_id'] for registration in registration_data if registration.get('event_ticket_id')]
        event_ticket_by_id = {
            event_ticket.id: event_ticket
            for event_ticket in request.env['event.event.ticket'].sudo().browse(event_ticket_ids)
        }

        if all(event_ticket.price == 0 for event_ticket in event_ticket_by_id.values()) and not request.website.sale_get_order().id:
            # all chosen tickets are free AND no existing SO -> skip SO and payment process
            return super()._create_attendees_from_registration_post(event, registration_data)

        order_sudo = request.website.sale_get_order(force_create=True)
        if order_sudo.state != 'draft':
            request.website.sale_reset()
            order_sudo = request.website.sale_get_order(force_create=True)

        tickets_data = defaultdict(int)
        for data in registration_data:
            event_ticket_id = data.get('event_ticket_id')
            if event_ticket_id:
                tickets_data[event_ticket_id] += 1

        cart_data = {}
        for ticket_id, count in tickets_data.items():
            ticket_sudo = event_ticket_by_id.get(ticket_id)
            cart_values = order_sudo._cart_update(
                product_id=ticket_sudo.product_id.id,
                add_qty=count,
                event_ticket_id=ticket_id,
            )
            cart_data[ticket_id] = cart_values['line_id']

        for data in registration_data:
            event_ticket_id = data.get('event_ticket_id')
            event_ticket = event_ticket_by_id.get(event_ticket_id)
            if event_ticket:
                data['sale_order_id'] = order_sudo.id
                data['sale_order_line_id'] = cart_data[event_ticket_id]

        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity

        return super()._create_attendees_from_registration_post(event, registration_data)

    @route()
    def registration_confirm(self, event, **post):
        res = super().registration_confirm(event, **post)

        registrations = self._process_attendees_form(event, post)
        order_sudo = request.website.sale_get_order()
        if not order_sudo.id:
            # order does not contain any lines related to the event, meaning we are confirming only free tickets of this event
            return res

        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info['event_ticket_id'] for info in registrations):
            if order_sudo.amount_total:
                request.session['sale_last_order_id'] = order_sudo.id
                return request.redirect("/shop/checkout")
            # free tickets -> order with amount = 0: auto-confirm, no checkout
            elif order_sudo:
                order_sudo.action_confirm()  # tde notsure: email sending ?
                request.website.sale_reset()

        return res

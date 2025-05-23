# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal
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

        if all(event_ticket.price == 0 for event_ticket in event_ticket_by_id.values()) and not request.cart.id:
            # all chosen tickets are free AND no existing SO -> skip SO and payment process
            return super()._create_attendees_from_registration_post(event, registration_data)

        order_sudo = request.cart or request.website._create_cart()
        tickets_data = defaultdict(int)
        for data in registration_data:
            event_slot_id = data.get('event_slot_id', False)
            event_ticket_id = data.get('event_ticket_id', False)
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
            cart_data[slot_id, ticket_id] = cart_values['line_id']

        for data in registration_data:
            event_slot_id = data.get('event_slot_id', False)
            event_ticket_id = data.get('event_ticket_id', False)
            event_ticket = event_ticket_by_id.get(event_ticket_id)
            if event_ticket:
                data['sale_order_id'] = order_sudo.id
                data['sale_order_line_id'] = cart_data[event_slot_id, event_ticket_id]

        return super()._create_attendees_from_registration_post(event, registration_data)

    @route()
    def registration_confirm(self, event, **post):
        res = super().registration_confirm(event, **post)

        registrations = self._process_attendees_form(event, post)
        order_sudo = request.cart
        if not any(line.event_ticket_id for line in order_sudo.order_line):
            # order does not contain any tickets, meaning we are confirming a free event
            return res

        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info['event_ticket_id'] for info in registrations):
            if order_sudo.amount_total:
                if order_sudo._is_anonymous_cart():
                    booked_by_partner, feedback_dict = CustomerPortal()._create_or_update_address(
                        request.env['res.partner'].sudo(),
                        order_sudo=order_sudo,
                        verify_address_values=False,
                        **registrations[0]
                    )
                    if not feedback_dict.get('invalid_fields'):
                        order_sudo._update_address(booked_by_partner.id, ['partner_id'])
                request.session['sale_last_order_id'] = order_sudo.id
                return request.redirect("/shop/checkout?try_skip_step=true")
            else:
                # Free order -> auto confirmation without checkout
                order_sudo.action_confirm()  # tde notsure: email sending ?
                request.website.sale_reset()
                request.session['sale_last_order_id'] = order_sudo.id
                return request.redirect("/shop/confirmation")

        return res

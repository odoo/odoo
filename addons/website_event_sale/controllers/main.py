# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request


class WebsiteEventSaleController(WebsiteEventController):

    @http.route(['/event/<model("event.event"):event>/register'], type='http', auth="public", website=True)
    def event_register(self, event, **post):
        event = event.with_context(pricelist=request.website.get_current_pricelist().id)
        return super(WebsiteEventSaleController, self).event_register(event, **post)

    def _process_tickets_details(self, data):
        ticket_post = {}
        for key, value in data.items():
            if not key.startswith('nb_register') or '-' not in key:
                continue
            items = key.split('-')
            if len(items) < 2:
                continue
            ticket_post[int(items[1])] = int(value)
        tickets = request.env['event.event.ticket'].browse(tuple(ticket_post))
        return [{'id': ticket.id, 'name': ticket.name, 'quantity': ticket_post[ticket.id], 'price': ticket.price} for ticket in tickets if ticket_post[ticket.id]]

    @http.route(['/event/<model("event.event"):event>/registration/confirm'], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        order = request.website.sale_get_order(force_create=1)
        attendee_ids = set()

        registrations = self._process_registration_details(post)
        for registration in registrations:
            ticket = request.env['event.event.ticket'].sudo().browse(int(registration['ticket_id']))
            cart_values = order.with_context(event_ticket_id=ticket.id, fixed_price=True)._cart_update(product_id=ticket.product_id.id, add_qty=1, registration_data=[registration])
            attendee_ids |= set(cart_values.get('attendee_ids', []))

        # free tickets -> order with amount = 0: auto-confirm, no checkout
        if not order.amount_total:
            order.action_confirm()  # tde notsure: email sending ?
            attendees = request.env['event.registration'].browse(list(attendee_ids)).sudo()
            # clean context and session, then redirect to the confirmation page
            request.website.sale_reset()
            return request.render("website_event.registration_complete", {
                'attendees': attendees,
                'event': event,
            })

        return request.redirect("/shop/checkout")

    def _add_event(self, event_name="New Event", context=None, **kwargs):
        product = request.env.ref('event_sale.product_product_event', raise_if_not_found=False)
        if product:
            context = dict(context or {}, default_event_ticket_ids=[[0, 0, {
                'name': _('Registration'),
                'product_id': product.id,
                'deadline': False,
                'seats_max': 1000,
                'price': 0,
            }]])
        return super(WebsiteEventSaleController, self)._add_event(event_name, context, **kwargs)

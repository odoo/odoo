# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request


class WebsiteEventSaleController(WebsiteEventController):

    @http.route()
    def event_register(self, event, **post):
        event = event.with_context(pricelist=request.website.id)
        if not request.context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            if pricelist:
                event = event.with_context(pricelist=pricelist.id)
        return super(WebsiteEventSaleController, self).event_register(event, **post)

    def _process_tickets_form(self, event, form_details):
        """ Add price information on ticket order """
        res = super(WebsiteEventSaleController, self)._process_tickets_form(event, form_details)
        for item in res:
            item['price'] = item['ticket']['price'] if item['ticket'] else 0
        return res

    def _create_attendees_from_registration_post(self, event, registration_data):
        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info.get('event_ticket_id') for info in registration_data):
            order = request.website.sale_get_order(force_create=1)

        for info in [r for r in registration_data if r.get('event_ticket_id')]:
            ticket = request.env['event.event.ticket'].sudo().browse(info['event_ticket_id'])
            cart_values = order.with_context(event_ticket_id=ticket.id, fixed_price=True)._cart_update(product_id=ticket.product_id.id, add_qty=1)
            info['sale_order_id'] = order.id
            info['sale_order_line_id'] = cart_values.get('line_id')

        return super(WebsiteEventSaleController, self)._create_attendees_from_registration_post(event, registration_data)

    @http.route()
    def registration_confirm(self, event, **post):
        res = super(WebsiteEventSaleController, self).registration_confirm(event, **post)

        registrations = self._process_attendees_form(event, post)

        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info['event_ticket_id'] for info in registrations):
            order = request.website.sale_get_order(force_create=False)
            if order.amount_total:
                return request.redirect("/shop/checkout")
            # free tickets -> order with amount = 0: auto-confirm, no checkout
            elif order:
                order.action_confirm()  # tde notsure: email sending ?
                request.website.sale_reset()

        return res

    def _add_event(self, event_name="New Event", context=None, **kwargs):
        product = request.env.ref('event_sale.product_product_event', raise_if_not_found=False)
        if product:
            context = dict(context or {}, default_event_ticket_ids=[[0, 0, {
                'name': _('Registration'),
                'product_id': product.id,
                'end_sale_date': False,
                'seats_max': 1000,
                'price': 0,
            }]])
        return super(WebsiteEventSaleController, self)._add_event(event_name, context, **kwargs)

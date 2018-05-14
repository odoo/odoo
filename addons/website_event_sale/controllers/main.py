# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_event.controllers.main import website_event
from openerp.addons.website_sale.controllers.main import get_pricelist
from openerp.tools.translate import _


class website_event(website_event):

    @http.route(['/event/<model("event.event"):event>/register'], type='http', auth="public", website=True)
    def event_register(self, event, **post):
        pricelist_id = int(get_pricelist())
        values = {
            'event': event.with_context(pricelist=pricelist_id),
            'main_object': event.with_context(pricelist=pricelist_id),
            'range': range,
        }
        return request.website.render("website_event.event_description_full", values)

    def _process_tickets_details(self, data):
        ticket_post = {}
        for key, value in data.iteritems():
            if not key.startswith('nb_register') or '-' not in key:
                continue
            items = key.split('-')
            if len(items) < 2:
                continue
            ticket_post[int(items[1])] = int(value)
        tickets = request.registry['event.event.ticket'].browse(request.cr, request.uid, ticket_post.keys(), request.context)
        return [{'id': ticket.id, 'name': ticket.name, 'quantity': ticket_post[ticket.id], 'price': ticket.price} for ticket in tickets if ticket_post[ticket.id]]

    @http.route(['/event/<model("event.event"):event>/registration/confirm'], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        cr, uid, context = request.cr, request.uid, request.context
        order = request.website.sale_get_order(force_create=1)
        attendee_ids = set()

        registrations = self._process_registration_details(post)
        for registration in registrations:
            ticket = request.registry['event.event.ticket'].browse(cr, SUPERUSER_ID, int(registration['ticket_id']), context=context)
            cart_values = order.with_context(event_ticket_id=ticket.id)._cart_update(product_id=ticket.product_id.id, add_qty=1, registration_data=[registration])
            attendee_ids |= set(cart_values.get('attendee_ids', []))

        # free tickets -> order with amount = 0: auto-confirm, no checkout
        if not order.amount_total:
            order.action_confirm()  # tde notsure: email sending ?
            attendees = request.registry['event.registration'].browse(cr, uid, list(attendee_ids), context=context).sudo()
            # clean context and session, then redirect to the confirmation page
            request.website.sale_reset(context=context)
            return request.website.render("website_event.registration_complete", {
                'attendees': attendees,
                'event': event,
            })

        return request.redirect("/shop/checkout")

    def _add_event(self, event_name="New Event", context={}, **kwargs):
        try:
            res_id = request.env.ref('event_sale.product_product_event').id
            context['default_event_ticket_ids'] = [[0, 0, {
                'name': _('Subscription'),
                'product_id': res_id,
                'deadline': False,
                'seats_max': 1000,
                'price': 0,
            }]]
        except ValueError:
            pass
        return super(website_event, self)._add_event(event_name, context, **kwargs)

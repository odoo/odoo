# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
            if not key.startswith('nb_register') or not '-' in key:
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

        registrations = self._process_registration_details(post)
        registration_ctx = dict(context, registration_force_draft=True)
        for registration in registrations:
            ticket = request.registry['event.event.ticket'].browse(cr, SUPERUSER_ID, int(registration['ticket_id']), context=context)
            order.with_context(event_ticket_id=ticket.id)._cart_update(product_id=ticket.product_id.id, add_qty=1)

            request.registry['event.registration'].create(cr, SUPERUSER_ID, {
                'name': registration.get('name'),
                'phone': registration.get('phone'),
                'email': registration.get('email'),
                'event_ticket_id': int(registration['ticket_id']),
                'partner_id': order.partner_id.id,
                'event_id': event.id,
                'origin': order.name,
            }, context=registration_ctx)

        return request.redirect("/shop/checkout")

    def _add_event(self, event_name="New Event", context={}, **kwargs):
        try:
            dummy, res_id = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'event_sale', 'product_product_event')
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

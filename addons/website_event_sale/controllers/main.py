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
from openerp.addons.website_sale.controllers.main import get_pricelist, website_sale
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

    @http.route(['/event/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, event_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        ticket_obj = request.registry.get('event.event.ticket')

        sale = False
        for key, value in post.items():
            quantity = int(value or "0")
            if not quantity:
                continue
            sale = True
            ticket_id = key.split("-")[0] == 'ticket' and int(key.split("-")[1]) or None
            ticket = ticket_obj.browse(cr, SUPERUSER_ID, ticket_id, context=context)
            order = request.website.sale_get_order(force_create=1)
            order.with_context(event_ticket_id=ticket.id)._cart_update(product_id=ticket.product_id.id, add_qty=quantity)

        if not sale:
            return request.redirect("/event/%s" % event_id)
        return request.redirect("/shop/checkout")

    def _add_event(self, event_name="New Event", context={}, **kwargs):
        try:
            dummy, res_id = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'event_sale', 'product_product_event')
            context['default_event_ticket_ids'] = [[0,0,{
                'name': _('Subscription'),
                'product_id': res_id,
                'deadline' : False,
                'seats_max': 1000,
                'price': 0,
            }]]
        except ValueError:
            pass
        return super(website_event, self)._add_event(event_name, context, **kwargs)


class website_sale(website_sale):

    @http.route(['/shop/get_unit_price'], type='json', auth="public", methods=['POST'], website=True)
    def get_unit_price(self, product_ids, add_qty, use_order_pricelist=False, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        res_ticket = {}
        if 'line_id' in kw:
            line = pool['sale.order.line'].browse(cr, SUPERUSER_ID, kw['line_id'])
            if line.event_ticket_id:
                if line.order_id.pricelist_id:
                    ticket = pool['event.event.ticket'].browse(cr, SUPERUSER_ID, line.event_ticket_id.id, context=dict(context, pricelist=line.order_id.pricelist_id.id))
                else:
                    ticket = line.event_ticket_id
                res_ticket = {ticket.product_id.id: ticket.price_reduce or ticket.price}
                product_ids.remove(ticket.product_id.id)
        res_options = super(website_sale, self).get_unit_price(product_ids, add_qty, use_order_pricelist, **kw)
        return dict(res_ticket.items() + res_options.items())

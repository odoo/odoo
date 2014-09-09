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
from openerp.tools.translate import _


class website_event(website_event):
    @http.route(['/event/add_cart'], type='http', auth="public", website=True, multilang=True)
    def add_cart(self, event_id, **post):
        user_obj = request.registry['res.users']
        order_line_obj = request.registry.get('sale.order.line')
        ticket_obj = request.registry.get('event.event.ticket')
        order_obj = request.registry.get('sale.order')
        website = request.registry['website']

        order = website.ecommerce_get_current_order(request.cr, request.uid, context=request.context)
        if not order:
            order = website.ecommerce_get_new_order(request.cr, request.uid, context=request.context)

        partner_id = user_obj.browse(request.cr, SUPERUSER_ID, request.uid,
                                     context=request.context).partner_id.id

        fields = [k for k, v in order_line_obj._columns.items()]
        values = order_line_obj.default_get(request.cr, SUPERUSER_ID, fields,
                                            context=request.context)

        _values = None
        for key, value in post.items():
            try:
                quantity = int(value)
                assert quantity > 0
            except:
                quantity = None
            ticket_id = key.split("-")[0] == 'ticket' and int(key.split("-")[1]) or None
            if not ticket_id or not quantity:
                continue
            ticket = ticket_obj.browse(request.cr, request.uid, ticket_id,
                                       context=request.context)

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            values['product_uom_qty'] = quantity
            values['price_unit'] = ticket.price
            values['order_id'] = order.id
            values['name'] = "%s: %s" % (ticket.event_id.name, ticket.name)

            # change and record value
            pricelist_id = order.pricelist_id and order.pricelist_id.id or False
            _values = order_line_obj.product_id_change(
                request.cr, SUPERUSER_ID, [], pricelist_id, ticket.product_id.id,
                partner_id=partner_id, context=request.context)['value']
            if 'tax_id' in _values:
                _values['tax_id'] = [(6, 0, _values['tax_id'])]
            _values.update(values)

            order_line_id = order_line_obj.create(request.cr, SUPERUSER_ID, _values, context=request.context)
            order_obj.write(request.cr, SUPERUSER_ID, [order.id], {'order_line': [(4, order_line_id)]}, context=request.context)

        if not _values:
            return request.redirect("/event/%s/" % event_id)
        return request.redirect("/shop/checkout")

    def _add_event(self, event_name="New Event", context={}, **kwargs):
        try:
            print kwargs
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




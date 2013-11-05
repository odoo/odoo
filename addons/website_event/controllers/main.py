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
from openerp.tools.translate import _
from openerp.addons import website_sale
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers
controllers = controllers()


from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools
import urllib


class website_event(http.Controller):
    _order = 'website_published desc, date_begin desc'

    @website.route(['/event/', '/event/page/<int:page>/'], type='http', auth="public", multilang=True)
    def events(self, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        event_obj = request.registry['event.event']
        type_obj = request.registry['event.type']
        country_obj = request.registry['res.country']

        searches.setdefault('date', 'all')
        searches.setdefault('type', 'all')
        searches.setdefault('country', 'all')

        domain_search = {}

        def sd(date):
            return date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        today = datetime.today()
        dates = [
            ['all', _('All Dates'), [(1, "=", 1)], 0],
            ['today', _('Today'), [
                ("date_begin", ">", sd(today)),
                ("date_begin", "<", sd(today + relativedelta(days=1)))],
                0],
            ['tomorrow', _('Tomorrow'), [
                ("date_begin", ">", sd(today + relativedelta(days=1))),
                ("date_begin", "<", sd(today + relativedelta(days=2)))],
                0],
            ['week', _('This Week'), [
                ("date_begin", ">=", sd(today + relativedelta(days=-today.weekday()))),
                ("date_begin", "<", sd(today  + relativedelta(days=6-today.weekday())))],
                0],
            ['nextweek', _('Next Week'), [
                ("date_begin", ">=", sd(today + relativedelta(days=7-today.weekday()))),
                ("date_begin", "<", sd(today  + relativedelta(days=13-today.weekday())))],
                0],
            ['month', _('This month'), [
                ("date_begin", ">=", sd(today.replace(day=1) + relativedelta(months=1))),
                ("date_begin", "<", sd(today.replace(day=1)  + relativedelta(months=1)))],
                0],
        ]

        # search domains
        current_date = dates[0][1]
        current_type = None
        current_country = None
        for date in dates:
            if searches["date"] == date[0]:
                domain_search["date"] = date[2]
                current_date = date[1]
        if searches["type"] != 'all':
            current_type = type_obj.browse(cr, uid, int(searches['type']), context=context)
            domain_search["type"] = [("type", "=", int(searches["type"]))]
        if searches["country"] != 'all':
            current_country = country_obj.browse(cr, uid, int(searches['country']), context=context)
            domain_search["country"] = [("country_id", "=", int(searches["country"]))]

        def dom_without(without):
            domain = SUPERUSER_ID != request.uid and [('website_published', '=', True)] or [(1, "=", 1)]
            for key, search in domain_search.items():
                if key != without:
                    domain += search
            return domain

        # count by domains without self search
        for date in dates:
            date[3] = event_obj.search(
                request.cr, request.uid, dom_without('date') + date[2],
                count=True, context=request.context)

        domain = dom_without('type')
        types = event_obj.read_group(
            request.cr, request.uid, domain, ["id", "type"], groupby="type",
            orderby="type", context=request.context)
        type_count = event_obj.search(request.cr, request.uid, domain,
                                      count=True, context=request.context)
        types.insert(0, {
            'type_count': type_count,
            'type': ("all", _("All Categories"))
        })

        domain = dom_without('country')
        countries = event_obj.read_group(
            request.cr, request.uid, domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_id_count = event_obj.search(request.cr, request.uid, domain,
                                            count=True, context=request.context)
        countries.insert(0, {
            'country_id_count': country_id_count,
            'country_id': ("all", _("All Countries"))
        })

        step = 5
        event_count = event_obj.search(
            request.cr, request.uid, dom_without("none"), count=True,
            context=request.context)
        pager = request.website.pager(url="/event/", total=event_count, page=page, step=step, scope=5)
        obj_ids = event_obj.search(
            request.cr, request.uid, dom_without("none"), limit=step,
            offset=pager['offset'], order=self._order, context=request.context)
        events_ids = event_obj.browse(request.cr, request.uid, obj_ids,
                                      context=request.context)

        values = {
            'current_date': current_date,
            'current_country': current_country,
            'current_type': current_type,
            'event_ids': events_ids,
            'dates': dates,
            'types': types,
            'countries': countries,
            'pager': pager,
            'searches': searches,
            'search_path': "?%s" % urllib.urlencode(searches),
        }

        return request.website.render("website_event.index", values)

    @website.route(['/event/<int:event_id>'], type='http', auth="public", multilang=True)
    def event(self, event_id=None, **post):
        event_obj = request.registry['event.event']
        event = event_obj.browse(request.cr, request.uid, event_id, dict(request.context, show_address_only=1))
        values = {
            'event_id': event,
            'main_object': event,
            'range': range,
            'float': float,
        }
        return request.website.render("website_event.event_description_full", values)

    @website.route(['/event/<int:event_id>/add_cart'], type='http', auth="public", multilang=True)
    def add_cart(self, event_id=None, **post):
        user_obj = request.registry['res.users']
        order_line_obj = request.registry.get('sale.order.line')
        ticket_obj = request.registry.get('event.event.ticket')

        order = request.context['website_sale_order']
        if not order:
            order = website_sale.controllers.main.get_order()

        partner_id = user_obj.browse(request.cr, SUPERUSER_ID, request.uid,
                                     context=request.context).partner_id.id

        fields = [k for k, v in order_line_obj._columns.items()]
        values = order_line_obj.default_get(request.cr, SUPERUSER_ID, fields,
                                            context=request.context)

        _values = None
        for key, value in post.items():
            try:
                quantity = int(value)
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

            ticket.check_registration_limits_before(quantity)

            # change and record value
            pricelist_id = order.pricelist_id and order.pricelist_id.id or False
            _values = order_line_obj.product_id_change(
                request.cr, SUPERUSER_ID, [], pricelist_id, ticket.product_id.id,
                partner_id=partner_id, context=request.context)['value']
            _values.update(values)

            order_line_id = order_line_obj.create(request.cr, SUPERUSER_ID,
                                                  _values, context=request.context)
            order.write({'order_line': [(4, order_line_id)]}, context=request.context)

        if not _values:
            return request.redirect("/event/%s/" % event_id)
        return request.redirect("/shop/checkout")

    @website.route(['/event/publish'], type='json', auth="public")
    def publish(self, id, object):
        # if a user publish an event, he publish all linked res.partner
        event = request.registry[object].browse(request.cr, request.uid, int(id))
        if not event.website_published:
            if event.organizer_id and not event.organizer_id.website_published:
                event.organizer_id.write({'website_published': True})
            if event.address_id and not event.address_id.website_published:
                event.address_id.write({'website_published': True})

        return controllers.publish(id, object)

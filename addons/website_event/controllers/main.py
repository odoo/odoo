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
from openerp.addons.website_sale.controllers.main import Ecommerce as Ecommerce
controllers = controllers()


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import tools
import urllib

class website_event(http.Controller):
    @website.route(['/event/', '/event/page/<int:page>'], type='http', auth="public", multilang=True)
    def events(self, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        event_obj = request.registry['event.event']
        type_obj = request.registry['event.type']
        country_obj = request.registry['res.country']

        searches.setdefault('date', 'all')
        searches.setdefault('type', 'all')
        searches.setdefault('country', 'all')

        domain_search = {}

        def sdn(date):
            return date.strftime('%Y-%m-%d 23:59:59')
        def sd(date):
            return date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        today = datetime.today()
        dates = [
            ['all', _('Next Events'), [("date_end", ">", sd(today))], 0],
            ['today', _('Today'), [
                ("date_end", ">", sd(today)),
                ("date_begin", "<", sdn(today))],
                0],
            ['week', _('This Week'), [
                ("date_end", ">=", sd(today + relativedelta(days=-today.weekday()))),
                ("date_begin", "<", sdn(today  + relativedelta(days=6-today.weekday())))],
                0],
            ['nextweek', _('Next Week'), [
                ("date_end", ">=", sd(today + relativedelta(days=7-today.weekday()))),
                ("date_begin", "<", sdn(today  + relativedelta(days=13-today.weekday())))],
                0],
            ['month', _('This month'), [
                ("date_end", ">=", sd(today.replace(day=1))),
                ("date_begin", "<", (today.replace(day=1) + relativedelta(months=1)).strftime('%Y-%m-%d 00:00:00'))],
                0],
            ['nextmonth', _('Next month'), [
                ("date_end", ">=", sd(today.replace(day=1) + relativedelta(months=1))),
                ("date_begin", "<", (today.replace(day=1)  + relativedelta(months=2)).strftime('%Y-%m-%d 00:00:00'))],
                0],
            ['old', _('Old Events'), [
                ("date_end", "<", today.strftime('%Y-%m-%d 00:00:00'))],
                0],
        ]

        # search domains
        current_date = None
        current_type = None
        current_country = None
        for date in dates:
            if searches["date"] == date[0]:
                domain_search["date"] = date[2]
                if date[0] != 'all':
                    current_date = date[1]
        if searches["type"] != 'all':
            current_type = type_obj.browse(cr, uid, int(searches['type']), context=context)
            domain_search["type"] = [("type", "=", int(searches["type"]))]
        if searches["country"] != 'all':
            current_country = country_obj.browse(cr, uid, int(searches['country']), context=context)
            domain_search["country"] = [("country_id", "=", int(searches["country"]))]

        def dom_without(without):
            domain = [('state', "in", ['draft','confirm','done'])]
            for key, search in domain_search.items():
                if key != without:
                    domain += search
            return domain

        # count by domains without self search
        for date in dates:
            if date[0] <> 'old':
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

        order = 'website_published desc, date_begin'
        if searches.get('date','all') == 'old':
            order = 'website_published desc, date_begin desc'
        obj_ids = event_obj.search(
            request.cr, request.uid, dom_without("none"), limit=step,
            offset=pager['offset'], order=order, context=request.context)
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

    @website.route(['/event/<model("event.event"):event>/page/<page:page>'], type='http', auth="public", multilang=True)
    def event_page(self, event, page, **post):
        values = {
            'event': event,
        }
        return request.website.render(page, values)

    @website.route(['/event/<model("event.event"):event>'], type='http', auth="public", multilang=True)
    def event(self, event=None, **post):
        if event.menu_id and event.menu_id.child_id:
            return request.redirect(event.menu_id.child_id[0].url)
        return request.redirect('/event/%s/register' % str(event.id))

    @website.route(['/event/<model("event.event"):event>/register'], type='http', auth="public", multilang=True)
    def event_register(self, event=None, **post):
        values = {
            'event': event,
            'range': range,
        }
        return request.website.render("website_event.event_description_full", values)

    @website.route(['/event/add_cart'], type='http', auth="public", multilang=True)
    def add_cart(self, event_id, **post):
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

    @website.route('/event/add_event/', type='http', auth="user", multilang=True, methods=['POST'])
    def add_event(self, event_name="New Event", **kwargs):
        Event = request.registry.get('event.event')
        date_begin = datetime.today() + timedelta(days=(15)) # FIXME: better defaults
        event_id = Event.create(request.cr, request.uid, {
            'name': event_name,
            'date_begin': date_begin.strftime('%Y-%m-%d'),
            'date_end': (date_begin + timedelta(days=(1))).strftime('%Y-%m-%d'),
        }, context=request.context)

        return request.redirect("/event/%s/?enable_editor=1" % event_id)

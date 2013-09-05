# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.addons import website_sale
from openerp.addons.website import website

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools
import urllib
import werkzeug


class website_event(http.Controller):

    @website.route(['/event/', '/event/page/<int:page>/'], type='http', auth="public")
    def events(self, page=1, **searches):
        website = request.registry['website']
        event_obj = request.registry['event.event']

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
        for date in dates:
            if searches.get("date") == date[0]:
                domain_search["date"] = date[2]
        if searches.get("type", "all") != 'all':
            domain_search["type"] = [("type", "=", int(searches.get("type")))]
        if searches.get("country", "all") != 'all':
            domain_search["country"] = [("country_id", "=", int(searches.get("country")))]

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
        pager = website.pager(url="/event/", total=event_count, page=page, step=step, scope=5)
        obj_ids = event_obj.search(
            request.cr, request.uid, dom_without("none"), limit=step,
            offset=pager['offset'], order="date_begin DESC", context=request.context)
        events_ids = event_obj.browse(request.cr, request.uid, obj_ids,
                                      context=request.context)

        values = {
            'event_ids': events_ids,
            'dates': dates,
            'types': types,
            'countries': countries,
            'pager': pager,
            'searches': searches,
            'search_path': "?%s" % urllib.urlencode(searches),
        }

        return request.webcontext.render("website_event.index", values)

    @website.route(['/event/<int:event_id>'], type='http', auth="public")
    def event(self, event_id=None, **post):
        event_obj = request.registry['event.event']
        values = {
            'event_id': event_obj.browse(request.cr, request.uid, event_id,
                                         dict({'show_address': 1} + request.context)),
            'message_ids': event_obj.browse(request.cr, request.uid, event_id,
                                            context=request.context).message_ids,
            'subscribe': post.get('subscribe'),
            'range': range
        }
        return request.webcontext.render("website_event.detail", values)

    @website.route(['/event/<int:event_id>/add_cart'], type='http', auth="public")
    def add_cart(self, event_id=None, **post):
        user_obj = request.registry['res.users']
        order_line_obj = request.registry.get('sale.order.line')
        ticket_obj = request.registry.get('event.event.ticket')

        order = request.webcontext['order']
        if not order:
            order = website_sale.controllers.main.get_order()

        partner_id = user_obj.browse(request.cr, SUPERUSER_ID, request.uid,
                                     context=request.context).partner_id.id

        fields = [k for k, v in order_line_obj._columns.items()]
        values = order_line_obj.default_get(request.cr, SUPERUSER_ID, fields,
                                            context=request.context)

        _values = None
        for key, value in post.items():
            quantity = int(value)
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
            return werkzeug.utils.redirect("/event/%s/" % event_id)
        return werkzeug.utils.redirect("/shop/checkout")

    @website.route(['/event/<int:event_id>/subscribe'], type='http', auth="public")
    def subscribe(self, event_id=None, **post):
        partner_obj = request.registry['res.partner']
        event_obj = request.registry['event.event']
        user_obj = request.registry['res.users']

        if event_id and 'subscribe' in post and (post.get('email') or not request.webcontext.is_public_user):
            if request.webcontext.is_public_user:
                partner_ids = partner_obj.search(
                    request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))],
                    context=request.context)
                if not partner_ids:
                    partner_data = {
                        "email": post.get('email'),
                        "name": "Subscribe: %s" % post.get('email')
                    }
                    partner_ids = [partner_obj.create(
                        request.cr, SUPERUSER_ID, partner_data, context=request.context)]
            else:
                partner_ids = [user_obj.browse(
                    request.cr, request.uid, request.uid,
                    context=request.context).partner_id.id]
            event_obj.check_access_rule(request.cr, request.uid, [event_id],
                                        'read', request.context)
            event_obj.message_subscribe(request.cr, SUPERUSER_ID, [event_id],
                                        partner_ids, request.context)

        return self.event(event_id=event_id, subscribe=post.get('email'))

    @website.route(['/event/<int:event_id>/unsubscribe'], type='http', auth="public")
    def unsubscribe(self, event_id=None, **post):
        partner_obj = request.registry['res.partner']
        event_obj = request.registry['event.event']
        user_obj = request.registry['res.users']

        if event_id and 'unsubscribe' in post and (post.get('email') or not request.webcontext.is_public_user):
            if request.webcontext.is_public_user:
                partner_ids = partner_obj.search(
                    request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))],
                    context=request.context)
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id.id]
            event_obj.check_access_rule(request.cr, request.uid, [event_id], 'read', request.context)
            event_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [event_id], partner_ids, request.context)

        return self.event(event_id=event_id, subscribe=None)

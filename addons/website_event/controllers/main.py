# -*- coding: utf-8 -*-

import babel.dates
import time
import re
import werkzeug.urls
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp import http
from openerp import tools, SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.http import request
from openerp.tools.translate import _


class website_event(http.Controller):
    @http.route(['/event', '/event/page/<int:page>', '/events', '/events/page/<int:page>'], type='http', auth="public", website=True)
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
            return date.replace(hour=23, minute=59, second=59).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

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
                ("date_begin", "<", sdn(today + relativedelta(days=6-today.weekday())))],
                0],
            ['nextweek', _('Next Week'), [
                ("date_end", ">=", sd(today + relativedelta(days=7-today.weekday()))),
                ("date_begin", "<", sdn(today + relativedelta(days=13-today.weekday())))],
                0],
            ['month', _('This month'), [
                ("date_end", ">=", sd(today.replace(day=1))),
                ("date_begin", "<", (today.replace(day=1) + relativedelta(months=1)).strftime('%Y-%m-%d 00:00:00'))],
                0],
            ['nextmonth', _('Next month'), [
                ("date_end", ">=", sd(today.replace(day=1) + relativedelta(months=1))),
                ("date_begin", "<", (today.replace(day=1) + relativedelta(months=2)).strftime('%Y-%m-%d 00:00:00'))],
                0],
            ['old', _('Old Events'), [
                ("date_end", "<", today.strftime('%Y-%m-%d 00:00:00'))],
                0],
        ]

        # search domains
        # TDE note: WTF ???
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
            domain_search["type"] = [("event_type_id", "=", int(searches["type"]))]

        if searches["country"] != 'all' and searches["country"] != 'online':
            current_country = country_obj.browse(cr, uid, int(searches['country']), context=context)
            domain_search["country"] = ['|', ("country_id", "=", int(searches["country"])), ("country_id", "=", False)]
        elif searches["country"] == 'online':
            domain_search["country"] = [("country_id", "=", False)]

        def dom_without(without):
            domain = [('state', "in", ['draft', 'confirm', 'done'])]
            for key, search in domain_search.items():
                if key != without:
                    domain += search
            return domain

        # count by domains without self search
        for date in dates:
            if date[0] != 'old':
                date[3] = event_obj.search(
                    request.cr, request.uid, dom_without('date') + date[2],
                    count=True, context=request.context)

        domain = dom_without('type')
        types = event_obj.read_group(
            request.cr, request.uid, domain, ["id", "event_type_id"], groupby="event_type_id",
            orderby="event_type_id", context=request.context)
        type_count = event_obj.search(request.cr, request.uid, domain,
                                      count=True, context=request.context)
        types.insert(0, {
            'event_type_id_count': type_count,
            'event_type_id': ("all", _("All Categories"))
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

        step = 10  # Number of events per page
        event_count = event_obj.search(
            request.cr, request.uid, dom_without("none"), count=True,
            context=request.context)
        pager = request.website.pager(
            url="/event",
            url_args={'date': searches.get('date'), 'type': searches.get('type'), 'country': searches.get('country')},
            total=event_count,
            page=page,
            step=step,
            scope=5)

        order = 'website_published desc, date_begin'
        if searches.get('date', 'all') == 'old':
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
            'search_path': "?%s" % werkzeug.url_encode(searches),
        }

        return request.website.render("website_event.index", values)

    @http.route(['/event/<model("event.event"):event>/page/<path:page>'], type='http', auth="public", website=True)
    def event_page(self, event, page, **post):
        values = {
            'event': event,
            'main_object': event
        }

        if '.' not in page:
            page = 'website_event.%s' % page

        try:
            request.website.get_template(page)
        except ValueError:
            # page not found
            values['path'] = re.sub(r"^website_event\.", '', page)
            values['from_template'] = 'website_event.default_page'  # .strip('website_event.')
            page = 'website.page_404'

        return request.website.render(page, values)

    @http.route(['/event/<model("event.event"):event>'], type='http', auth="public", website=True)
    def event(self, event, **post):
        if event.menu_id and event.menu_id.child_id:
            target_url = event.menu_id.child_id[0].url
        else:
            target_url = '/event/%s/register' % str(event.id)
        if post.get('enable_editor') == '1':
            target_url += '?enable_editor=1'
        return request.redirect(target_url)

    @http.route(['/event/<model("event.event"):event>/register'], type='http', auth="public", website=True)
    def event_register(self, event, **post):
        values = {
            'event': event,
            'main_object': event,
            'range': range,
        }
        return request.website.render("website_event.event_description_full", values)

    @http.route('/event/add_event', type='http', auth="user", methods=['POST'], website=True)
    def add_event(self, event_name="New Event", **kwargs):
        return self._add_event(event_name, request.context, **kwargs)

    def _add_event(self, event_name=None, context={}, **kwargs):
        if not event_name:
            event_name = _("New Event")
        Event = request.registry.get('event.event')
        date_begin = datetime.today() + timedelta(days=(14))
        vals = {
            'name': event_name,
            'date_begin': date_begin.strftime('%Y-%m-%d'),
            'date_end': (date_begin + timedelta(days=(1))).strftime('%Y-%m-%d'),
            'seats_available': 1000,
        }
        event_id = Event.create(request.cr, request.uid, vals, context=context)
        event = Event.browse(request.cr, request.uid, event_id, context=context)
        return request.redirect("/event/%s/register?enable_editor=1" % slug(event))

    def get_formated_date(self, event):
        context = request.context
        start_date = datetime.strptime(event.date_begin, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
        end_date = datetime.strptime(event.date_end, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
        month = babel.dates.get_month_names('abbreviated', locale=context.get('lang', 'en_US'))[start_date.month]
        return _('%(month)s %(start_day)s%(end_day)s') % {
            'month': month,
            'start_day': start_date.strftime("%e"),
            'end_day': (end_date != start_date and ("-"+end_date.strftime("%e")) or "")
        }

    @http.route('/event/get_country_event_list', type='http', auth='public', website=True)
    def get_country_events(self, **post):
        cr, uid, context, event_ids = request.cr, request.uid, request.context, []
        country_obj = request.registry['res.country']
        event_obj = request.registry['event.event']
        country_code = request.session['geoip'].get('country_code')
        result = {'events': [], 'country': False}
        if country_code:
            country_ids = country_obj.search(cr, uid, [('code', '=', country_code)], context=context)
            event_ids = event_obj.search(cr, uid, ['|', ('address_id', '=', None), ('country_id.code', '=', country_code), ('date_begin', '>=', time.strftime('%Y-%m-%d 00:00:00')), ('state', '=', 'confirm')], order="date_begin", context=context)
        if not event_ids:
            event_ids = event_obj.search(cr, uid, [('date_begin', '>=', time.strftime('%Y-%m-%d 00:00:00')), ('state', '=', 'confirm')], order="date_begin", context=context)
        for event in event_obj.browse(cr, uid, event_ids, context=context)[:6]:
            if country_code and event.country_id.code == country_code:
                result['country'] = country_obj.browse(cr, uid, country_ids[0], context=context)
            result['events'].append({
                "date": self.get_formated_date(event),
                "event": event,
                "url": event.website_url})
        return request.website.render("website_event.country_events_list", result)

    def _process_tickets_details(self, data):
        nb_register = int(data.get('nb_register-0', 0))
        if nb_register:
            return [{'id': 0, 'name': 'Subscription', 'quantity': nb_register, 'price': 0}]
        return []

    @http.route(['/event/<model("event.event"):event>/registration/new'], type='json', auth="public", methods=['POST'], website=True)
    def registration_new(self, event, **post):
        tickets = self._process_tickets_details(post)
        if not tickets:
            return request.redirect("/event/%s" % slug(event))
        return request.website._render("website_event.registration_attendee_details", {'tickets': tickets, 'event': event})

    def _process_registration_details(self, details):
        ''' Process data posted from the attendee details form. '''
        registrations = {}
        global_values = {}
        for key, value in details.iteritems():
            counter, field_name = key.split('-', 1)
            if counter == '0':
                global_values[field_name] = value
            else:
                registrations.setdefault(counter, dict())[field_name] = value
        for key, value in global_values.iteritems():
            for registration in registrations.values():
                registration[key] = value
        return registrations.values()

    @http.route(['/event/<model("event.event"):event>/registration/confirm'], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Registration = request.registry['event.registration']
        registrations = self._process_registration_details(post)

        registration_ids = []
        for registration in registrations:
            registration['event_id'] = event
            registration_ids.append(
                Registration.create(
                    cr, SUPERUSER_ID,
                    Registration._prepare_attendee_values(cr, uid, registration),
                    context=context))

        attendees = Registration.browse(cr, uid, registration_ids, context=context)
        return request.website.render("website_event.registration_complete", {
            'attendees': attendees,
            'event': event,
        })

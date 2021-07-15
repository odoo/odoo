# -*- coding: utf-8 -*-

import collections
import babel.dates
import re
import werkzeug
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.exceptions import NotFound

from ast import literal_eval
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.event.controllers.main import EventController
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang, format_date


class WebsiteEventController(http.Controller):

    def sitemap_event(env, rule, qs):
        if not qs or qs.lower() in '/events':
            yield {'loc': '/events'}

    @http.route(['/event', '/event/page/<int:page>', '/events', '/events/page/<int:page>'], type='http', auth="public", website=True, sitemap=sitemap_event)
    def events(self, page=1, **searches):
        Event = request.env['event.event']
        SudoEventType = request.env['event.type'].sudo()

        searches.setdefault('search', '')
        searches.setdefault('date', 'all')
        searches.setdefault('tags', '')
        searches.setdefault('type', 'all')
        searches.setdefault('country', 'all')

        website = request.website
        today = fields.Datetime.today()

        def sdn(date):
            return fields.Datetime.to_string(date.replace(hour=23, minute=59, second=59))

        def sd(date):
            return fields.Datetime.to_string(date)

        def get_month_filter_domain(filter_name, months_delta):
            first_day_of_the_month = today.replace(day=1)
            filter_string = _('This month') if months_delta == 0 \
                else format_date(request.env, value=today + relativedelta(months=months_delta),
                                 date_format='LLLL', lang_code=get_lang(request.env).code).capitalize()
            return [filter_name, filter_string, [
                ("date_end", ">=", sd(first_day_of_the_month + relativedelta(months=months_delta))),
                ("date_begin", "<", sd(first_day_of_the_month + relativedelta(months=months_delta+1)))],
                0]

        dates = [
            ['all', _('Upcoming Events'), [("date_end", ">", sd(today))], 0],
            ['today', _('Today'), [
                ("date_end", ">", sd(today)),
                ("date_begin", "<", sdn(today))],
                0],
            get_month_filter_domain('month', 0),
            ['old', _('Past Events'), [
                ("date_end", "<", sd(today))],
                0],
        ]

        # search domains
        domain_search = {'website_specific': website.website_domain()}

        if searches['search']:
            domain_search['search'] = [('name', 'ilike', searches['search'])]

        search_tags = self._extract_searched_event_tags(searches)
        if search_tags:
            # Example: You filter on age: 10-12 and activity: football.
            # Doing it this way allows to only get events who are tagged "age: 10-12" AND "activity: football".
            # Add another tag "age: 12-15" to the search and it would fetch the ones who are tagged:
            # ("age: 10-12" OR "age: 12-15") AND "activity: football
            grouped_tags = defaultdict(list)
            for tag in search_tags:
                grouped_tags[tag.category_id].append(tag)
            domain_search['tags'] = []
            for group in grouped_tags:
                domain_search['tags'] = expression.AND([domain_search['tags'], [('tag_ids', 'in', [tag.id for tag in grouped_tags[group]])]])

        current_date = None
        current_type = None
        current_country = None
        for date in dates:
            if searches["date"] == date[0]:
                domain_search["date"] = date[2]
                if date[0] != 'all':
                    current_date = date[1]

        if searches["type"] != 'all':
            current_type = SudoEventType.browse(int(searches['type']))
            domain_search["type"] = [("event_type_id", "=", int(searches["type"]))]

        if searches["country"] != 'all' and searches["country"] != 'online':
            current_country = request.env['res.country'].browse(int(searches['country']))
            domain_search["country"] = ['|', ("country_id", "=", int(searches["country"])), ("country_id", "=", False)]
        elif searches["country"] == 'online':
            domain_search["country"] = [("country_id", "=", False)]

        def dom_without(without):
            domain = []
            for key, search in domain_search.items():
                if key != without:
                    domain += search
            return domain

        # count by domains without self search
        for date in dates:
            if date[0] != 'old':
                date[3] = Event.search_count(dom_without('date') + date[2])

        domain = dom_without('type')

        domain = dom_without('country')
        countries = Event.read_group(domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        countries.insert(0, {
            'country_id_count': sum([int(country['country_id_count']) for country in countries]),
            'country_id': ("all", _("All Countries"))
        })

        step = 12  # Number of events per page
        event_count = Event.search_count(dom_without("none"))
        pager = website.pager(
            url="/event",
            url_args=searches,
            total=event_count,
            page=page,
            step=step,
            scope=5)

        order = 'date_begin'
        if searches.get('date', 'all') == 'old':
            order = 'date_begin desc'
        order = 'is_published desc, ' + order
        events = Event.search(dom_without("none"), limit=step, offset=pager['offset'], order=order)

        keep = QueryURL('/event', **{key: value for key, value in searches.items() if (key == 'search' or value != 'all')})

        values = {
            'current_date': current_date,
            'current_country': current_country,
            'current_type': current_type,
            'event_ids': events,  # event_ids used in website_event_track so we keep name as it is
            'dates': dates,
            'categories': request.env['event.tag.category'].search([]),
            'countries': countries,
            'pager': pager,
            'searches': searches,
            'search_tags': search_tags,
            'keep': keep,
        }

        if searches['date'] == 'old':
            # the only way to display this content is to set date=old so it must be canonical
            values['canonical_params'] = OrderedMultiDict([('date', 'old')])

        return request.render("website_event.index", values)

    @http.route(['''/event/<model("event.event"):event>/page/<path:page>'''], type='http', auth="public", website=True, sitemap=False)
    def event_page(self, event, page, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        values = {
            'event': event,
        }

        if '.' not in page:
            page = 'website_event.%s' % page

        try:
            # Every event page view should have its own SEO.
            values['seo_object'] = request.website.get_template(page)
            values['main_object'] = event
        except ValueError:
            # page not found
            values['path'] = re.sub(r"^website_event\.", '', page)
            values['from_template'] = 'website_event.default_page'  # .strip('website_event.')
            page = request.website.is_publisher() and 'website.page_404' or 'http_routing.404'

        return request.render(page, values)

    @http.route(['''/event/<model("event.event"):event>'''], type='http', auth="public", website=True, sitemap=True)
    def event(self, event, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        if event.menu_id and event.menu_id.child_id:
            target_url = event.menu_id.child_id[0].url
        else:
            target_url = '/event/%s/register' % str(event.id)
        if post.get('enable_editor') == '1':
            target_url += '?enable_editor=1'
        return request.redirect(target_url)

    @http.route(['''/event/<model("event.event"):event>/register'''], type='http', auth="public", website=True, sitemap=False)
    def event_register(self, event, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        values = self._prepare_event_register_values(event, **post)
        return request.render("website_event.event_description_full", values)

    def _prepare_event_register_values(self, event, **post):
        """Return the require values to render the template."""
        urls = event._get_event_resource_urls()
        return {
            'event': event,
            'main_object': event,
            'range': range,
            'google_url': urls.get('google_url'),
            'iCal_url': urls.get('iCal_url'),
        }

    @http.route('/event/add_event', type='json', auth="user", methods=['POST'], website=True)
    def add_event(self, event_name="New Event", **kwargs):
        event = self._add_event(event_name, request.context)
        return "/event/%s/register?enable_editor=1" % slug(event)

    def _add_event(self, event_name=None, context=None, **kwargs):
        if not event_name:
            event_name = _("New Event")
        date_begin = datetime.today() + timedelta(days=(14))
        vals = {
            'name': event_name,
            'date_begin': fields.Date.to_string(date_begin),
            'date_end': fields.Date.to_string((date_begin + timedelta(days=(1)))),
            'seats_available': 1000,
            'website_id': request.website.id,
        }
        return request.env['event.event'].with_context(context or {}).create(vals)

    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('abbreviated', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s%s') % (month, start_date.strftime("%e"), (end_date != start_date and ("-" + end_date.strftime("%e")) or ""))

    @http.route('/event/get_country_event_list', type='json', auth='public', website=True)
    def get_country_events(self, **post):
        Event = request.env['event.event']
        country_code = request.session['geoip'].get('country_code')
        result = {'events': [], 'country': False}
        events = None
        domain = request.website.website_domain()
        if country_code:
            country = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            events = Event.search(domain + ['|', ('address_id', '=', None), ('country_id.code', '=', country_code), ('date_begin', '>=', '%s 00:00:00' % fields.Date.today())], order="date_begin")
        if not events:
            events = Event.search(domain + [('date_begin', '>=', '%s 00:00:00' % fields.Date.today())], order="date_begin")
        for event in events:
            if country_code and event.country_id.code == country_code:
                result['country'] = country
            result['events'].append({
                "date": self.get_formated_date(event),
                "event": event,
                "url": event.website_url})
        return request.env['ir.ui.view']._render_template("website_event.country_events_list", result)

    def _process_tickets_form(self, event, form_details):
        """ Process posted data about ticket order. Generic ticket are supported
        for event without tickets (generic registration).

        :return: list of order per ticket: [{
            'id': if of ticket if any (0 if no ticket),
            'ticket': browse record of ticket if any (None if no ticket),
            'name': ticket name (or generic 'Registration' name if no ticket),
            'quantity': number of registrations for that ticket,
        }, {...}]
        """
        ticket_order = {}
        for key, value in form_details.items():
            registration_items = key.split('nb_register-')
            if len(registration_items) != 2:
                continue
            ticket_order[int(registration_items[1])] = int(value)

        ticket_dict = dict((ticket.id, ticket) for ticket in request.env['event.event.ticket'].search([
            ('id', 'in', [tid for tid in ticket_order.keys() if tid]),
            ('event_id', '=', event.id)
        ]))

        return [{
            'id': tid if ticket_dict.get(tid) else 0,
            'ticket': ticket_dict.get(tid),
            'name': ticket_dict[tid]['name'] if ticket_dict.get(tid) else _('Registration'),
            'quantity': count,
        } for tid, count in ticket_order.items() if count]

    @http.route(['/event/<model("event.event"):event>/registration/new'], type='json', auth="public", methods=['POST'], website=True)
    def registration_new(self, event, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        tickets = self._process_tickets_form(event, post)
        availability_check = True
        if event.seats_limited:
            ordered_seats = 0
            for ticket in tickets:
                ordered_seats += ticket['quantity']
            if event.seats_available < ordered_seats:
                availability_check = False
        if not tickets:
            return False
        return request.env['ir.ui.view']._render_template("website_event.registration_attendee_details", {'tickets': tickets, 'event': event, 'availability_check': availability_check})

    def _process_attendees_form(self, event, form_details):
        """ Process data posted from the attendee details form.

        :param form_details: posted data from frontend registration form, like
            {'1-name': 'r', '1-email': 'r@r.com', '1-phone': '', '1-event_ticket_id': '1'}
        """
        allowed_fields = request.env['event.registration']._get_website_registration_allowed_fields()
        registration_fields = {key: v for key, v in request.env['event.registration']._fields.items() if key in allowed_fields}
        registrations = {}
        global_values = {}
        for key, value in form_details.items():
            counter, attr_name = key.split('-', 1)
            field_name = attr_name.split('-')[0]
            if field_name not in registration_fields:
                continue
            elif isinstance(registration_fields[field_name], (fields.Many2one, fields.Integer)):
                value = int(value) or False  # 0 is considered as a void many2one aka False
            else:
                value = value

            if counter == '0':
                global_values[attr_name] = value
            else:
                registrations.setdefault(counter, dict())[attr_name] = value
        for key, value in global_values.items():
            for registration in registrations.values():
                registration[key] = value

        return list(registrations.values())

    def _create_attendees_from_registration_post(self, event, registration_data):
        """ Also try to set a visitor (from request) and
        a partner (if visitor linked to a user for example). Purpose is to gather
        as much informations as possible, notably to ease future communications.
        Also try to update visitor informations based on registration info. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()
        visitor_values = {}

        registrations_to_create = []
        for registration_values in registration_data:
            registration_values['event_id'] = event.id
            if not registration_values.get('partner_id') and visitor_sudo.partner_id:
                registration_values['partner_id'] = visitor_sudo.partner_id.id
            elif not registration_values.get('partner_id'):
                registration_values['partner_id'] = request.env.user.partner_id.id

            if visitor_sudo:
                # registration may give a name to the visitor, yay
                if registration_values.get('name') and not visitor_sudo.name and not visitor_values.get('name'):
                    visitor_values['name'] = registration_values['name']
                # update registration based on visitor
                registration_values['visitor_id'] = visitor_sudo.id

            registrations_to_create.append(registration_values)

        if visitor_values:
            visitor_sudo.write(visitor_values)

        return request.env['event.registration'].sudo().create(registrations_to_create)

    @http.route(['''/event/<model("event.event"):event>/registration/confirm'''], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        registrations = self._process_attendees_form(event, post)
        attendees_sudo = self._create_attendees_from_registration_post(event, registrations)

        return request.render("website_event.registration_complete",
            self._get_registration_confirm_values(event, attendees_sudo))

    def _get_registration_confirm_values(self, event, attendees_sudo):
        urls = event._get_event_resource_urls()
        return {
            'attendees': attendees_sudo,
            'event': event,
            'google_url': urls.get('google_url'),
            'iCal_url': urls.get('iCal_url')
        }

    def _extract_searched_event_tags(self, searches):
        tags = request.env['event.tag']
        if searches.get('tags'):
            try:
                tag_ids = literal_eval(searches['tags'])
            except:
                pass
            else:
                # perform a search to filter on existing / valid tags implicitely + apply rules on color
                tags = request.env['event.tag'].search([('id', 'in', tag_ids)])
        return tags

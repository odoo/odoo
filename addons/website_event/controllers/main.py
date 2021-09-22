# -*- coding: utf-8 -*-

import babel.dates
import pytz
import re
import werkzeug

from ast import literal_eval
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.exceptions import NotFound

from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang


class WebsiteEventController(http.Controller):

    def sitemap_event(env, rule, qs):
        if not qs or qs.lower() in '/events':
            yield {'loc': '/events'}

    # ------------------------------------------------------------
    # EVENT LIST
    # ------------------------------------------------------------

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

        step = 12  # Number of events per page

        options = {
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not searches.get('noFuzzy'),
            'date': searches.get('date'),
            'tags': searches.get('tags'),
            'type': searches.get('type'),
            'country': searches.get('country'),
        }
        order = 'date_begin'
        if searches.get('date', 'all') == 'old':
            order = 'date_begin desc'
        order = 'is_published desc, ' + order
        search = searches.get('search')
        event_count, details, fuzzy_search_term = website._search_with_fuzzy("events", search,
            limit=page * step, order=order, options=options)
        event_details = details[0]
        events = event_details.get('results', Event)
        events = events[(page - 1) * step:page * step]

        # count by domains without self search
        domain_search = [('name', 'ilike', fuzzy_search_term or searches['search'])] if searches['search'] else []

        no_date_domain = event_details['no_date_domain']
        dates = event_details['dates']
        for date in dates:
            if date[0] != 'old':
                date[3] = Event.search_count(expression.AND(no_date_domain) + domain_search + date[2])

        no_country_domain = event_details['no_country_domain']
        countries = Event.read_group(expression.AND(no_country_domain) + domain_search, ["id", "country_id"],
            groupby="country_id", orderby="country_id")
        countries.insert(0, {
            'country_id_count': sum([int(country['country_id_count']) for country in countries]),
            'country_id': ("all", _("All Countries"))
        })

        search_tags = event_details['search_tags']
        current_date = event_details['current_date']
        current_type = None
        current_country = None

        if searches["type"] != 'all':
            current_type = SudoEventType.browse(int(searches['type']))

        if searches["country"] != 'all' and searches["country"] != 'online':
            current_country = request.env['res.country'].browse(int(searches['country']))

        pager = website.pager(
            url="/event",
            url_args=searches,
            total=event_count,
            page=page,
            step=step,
            scope=5)

        keep = QueryURL('/event', **{key: value for key, value in searches.items() if (key == 'search' or value != 'all')})

        searches['search'] = fuzzy_search_term or search

        values = {
            'current_date': current_date,
            'current_country': current_country,
            'current_type': current_type,
            'event_ids': events,  # event_ids used in website_event_track so we keep name as it is
            'dates': dates,
            'categories': request.env['event.tag.category'].search([('is_published', '=', True)]),
            'countries': countries,
            'pager': pager,
            'searches': searches,
            'search_tags': search_tags,
            'keep': keep,
            'search_count': event_count,
            'original_search': fuzzy_search_term and search,
        }

        if searches['date'] == 'old':
            # the only way to display this content is to set date=old so it must be canonical
            values['canonical_params'] = OrderedMultiDict([('date', 'old')])

        return request.render("website_event.index", values)

    # ------------------------------------------------------------
    # EVENT PAGE
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/page/<path:page>'''], type='http', auth="public", website=True, sitemap=False)
    def event_page(self, event, page, **post):
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
        if event.menu_id and event.menu_id.child_id:
            target_url = event.menu_id.child_id[0].url
        else:
            target_url = '/event/%s/register' % str(event.id)
        if post.get('enable_editor') == '1':
            target_url += '?enable_editor=1'
        return request.redirect(target_url)

    @http.route(['''/event/<model("event.event"):event>/register'''], type='http', auth="public", website=True, sitemap=False)
    def event_register(self, event, **post):
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

        ticket_dict = dict((ticket.id, ticket) for ticket in request.env['event.event.ticket'].sudo().search([
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
        default_first_attendee = {}
        if not request.env.user._is_public():
            default_first_attendee = {
                "name": request.env.user.name,
                "email": request.env.user.email,
                "phone": request.env.user.mobile or request.env.user.phone,
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_first_attendee = {
                    "name": visitor.name,
                    "email": visitor.email,
                    "phone": visitor.mobile,
                }
        return request.env['ir.ui.view']._render_template("website_event.registration_attendee_details", {
            'tickets': tickets,
            'event': event,
            'availability_check': availability_check,
            'default_first_attendee': default_first_attendee,
        })

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
                registration_values['partner_id'] = False if request.env.user._is_public() else request.env.user.partner_id.id

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
        registrations = self._process_attendees_form(event, post)
        attendees_sudo = self._create_attendees_from_registration_post(event, registrations)

        return request.redirect(('/event/%s/registration/success?' % event.id) + werkzeug.urls.url_encode({'registration_ids': ",".join([str(id) for id in attendees_sudo.ids])}))

    @http.route(['/event/<model("event.event"):event>/registration/success'], type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def event_registration_success(self, event, registration_ids):
        # fetch the related registrations, make sure they belong to the correct visitor / event pair
        visitor = request.env['website.visitor']._get_visitor_from_request()
        if not visitor:
            raise NotFound()
        attendees_sudo = request.env['event.registration'].sudo().search([
            ('id', 'in', [str(registration_id) for registration_id in registration_ids.split(',')]),
            ('event_id', '=', event.id),
            ('visitor_id', '=', visitor.id),
        ])
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

    # ------------------------------------------------------------
    # EDITOR (NEW EVENT)
    # ------------------------------------------------------------

    @http.route('/event/add_event', type='json', auth="user", methods=['POST'], website=True)
    def add_event(self, name, event_start, event_end, address_values, **kwargs):
        values = self._prepare_event_values(name, event_start, event_end, address_values)
        event = request.env['event.event'].create(values)
        return "/event/%s/register?enable_editor=1" % slug(event)

    def _prepare_event_values(self, name, event_start, event_end, address_values=None):
        """
        Return the values to create a new event.
        event_start,event_date are datetimes in the user tz.
        address_values is used to either choose an existing location or create one as we allow it in the frontend.
        """
        date_begin = parse(event_start).astimezone(pytz.utc).replace(tzinfo=None)
        date_end = parse(event_end).astimezone(pytz.utc).replace(tzinfo=None)
        address_id = request.env['res.partner']
        if address_values:
            (address_pid, address_vals) = int(address_values[0]), address_values[1]
            address_id = address_pid
            if address_pid == 0:
                address_id = request.env['res.partner'].create(address_vals).id
        return {
            'name': name,
            'date_begin': date_begin,
            'date_end': date_end,
            'address_id': address_id,
            'seats_available': 1000,
            'website_id': request.website.id,
            'event_ticket_ids': request.env['event.event.ticket'],
        }

    # ------------------------------------------------------------
    # TOOLS (JSON)
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # TOOLS (HELPERS)
    # ------------------------------------------------------------

    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('abbreviated', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s%s') % (month, start_date.strftime("%e"), (end_date != start_date and ("-" + end_date.strftime("%e")) or ""))

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

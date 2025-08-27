import babel.dates
import werkzeug

from ast import literal_eval
from collections import Counter
from datetime import datetime
from werkzeug.exceptions import NotFound

from odoo import fields, http, _
from odoo.addons.website.controllers.main import QueryURL
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.tools import lazy
from odoo.tools.translate import LazyTranslate
from odoo.exceptions import UserError, ValidationError

_lt = LazyTranslate(__name__)


class WebsiteEventController(http.Controller):

    def sitemap_event(env, rule, qs):
        if not qs or qs.lower() in '/events':
            yield {'loc': '/events'}

    # ------------------------------------------------------------
    # EVENT LIST
    # ------------------------------------------------------------

    def _get_events_search_options(self, slug_tags, **post):
        return {
            'displayDescription': True,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not post.get('noFuzzy'),
            'date': post.get('date'),
            'tags': slug_tags or post.get('tags'),
            'type': post.get('type'),
            'country': post.get('country'),
        }

    @http.route([
        path
        for base in ('event', 'events')
        for path in [
            f'/{base}',
            f'/{base}/page/<int:page>',
            f'/{base}/tags/<string:slug_tags>',
            f'/{base}/tags/<string:slug_tags>/page/<int:page>',
        ]
    ], type='http', auth="public", website=True, sitemap=sitemap_event, list_as_website_content=_lt("Events"))
    def events(self, page=1, slug_tags=None, **searches):
        if (slug_tags or searches.get('tags', '[]').count(',') > 0) and request.httprequest.method == 'GET' and not searches.get('prevent_redirect'):
            # Previously, the tags were searched using GET, which caused issues with crawlers (too many hits)
            # We replaced those with POST to avoid that, but it's not sufficient as bots "remember" crawled pages for a while
            # This permanent redirect is placed to instruct the bots that this page is no longer valid
            # Note: We allow a single tag to be GET, to keep crawlers & indexes on those pages
            # What we really want to avoid is combinatorial explosions
            # (Tags are formed as a JSON array, so we count ',' to keep it simple)
            # TODO: remove in a few stable versions (v19?), including the "prevent_redirect" param in templates
            return request.redirect('/event', code=301)

        Event = request.env['event.event']
        SudoEventType = request.env['event.type'].sudo()

        searches.setdefault('search', '')
        searches.setdefault('date', 'scheduled')
        searches.setdefault('tags', '')
        searches.setdefault('type', 'all')
        searches.setdefault('country', 'all')
        # The previous name of the 'scheduled' filter is 'upcoming' and may still be present in URL's saved by users.
        if searches['date'] == 'upcoming':
            searches['date'] = 'scheduled'

        website = request.website

        step = 12  # Number of events per page

        options = self._get_events_search_options(slug_tags, **searches)
        order = 'date_begin'
        if searches.get('date', 'scheduled') == 'old':
            order = 'date_begin desc'
        order = 'is_published desc, ' + order + ', id desc'
        search = searches.get('search')
        event_count, details, fuzzy_search_term = website._search_with_fuzzy("events", search,
            limit=page * step, order=order, options=options)
        event_details = details[0]
        events = event_details.get('results', Event)
        events = events[(page - 1) * step:page * step]

        # count by domains without self search
        domain_search = Domain('name', 'ilike', fuzzy_search_term or searches['search']) if searches['search'] else Domain.TRUE

        no_date_domain = Domain.AND(event_details['no_date_domain'])
        dates = event_details['dates']
        for date in dates:
            if date[0] not in ['all', 'old']:
                date[3] = Event.search_count(no_date_domain & domain_search & Domain(date[2]))

        no_country_domain = Domain.AND(event_details['no_country_domain'])
        country_groups = Event._read_group(
            no_country_domain & domain_search,
            ["country_id"], ["__count"], order="country_id")
        countries = [{
            'country_id_count': sum(count for __, count in country_groups),
            'country_id': (0, _("All Countries")),
        }]
        for g_country, count in country_groups:
            countries.append({
                'country_id_count': count,
                'country_id': g_country and (g_country.id, g_country.sudo().display_name),
            })

        search_tags = self._extract_searched_event_tags(searches, slug_tags)
        current_date = event_details['current_date']
        current_type = None
        current_country = None

        if searches["type"] != 'all':
            current_type = SudoEventType.browse(int(searches['type']))

        if searches["country"] != 'all' and searches["country"] != 'online':
            current_country = request.env['res.country'].browse(int(searches['country']))

        pager = website.pager(
            url=f"/event/tags/{slug_tags}" if slug_tags else "/event",
            url_args=searches,
            total=event_count,
            page=page,
            step=step,
            scope=5)

        keep = QueryURL('/event', ['tags'],
            tags=slug_tags,
            **{
            key: value for key, value in searches.items() if (
                key != 'tags' and (
                    key == 'search' or
                    (value != 'scheduled' if key == 'date' else value != 'all'))
                )
            })

        searches['search'] = fuzzy_search_term or search

        values = {
            'current_date': current_date,
            'current_country': current_country,
            'current_type': current_type,
            'event_ids': events,  # event_ids used in website_event_track so we keep name as it is
            'dates': dates,
            'categories': request.env['event.tag.category'].search([
                ('is_published', '=', True), '|', ('website_id', '=', website.id), ('website_id', '=', False)
            ]),
            'countries': countries,
            'pager': pager,
            'searches': searches,
            'search_tags': search_tags,
            'keep_event_url': keep,
            'slugify_tags': self._slugify_tags,
            'search_count': event_count,
            'original_search': fuzzy_search_term and search,
            'website': website
        }

        return request.render("website_event.index", values)

    # ------------------------------------------------------------
    # EVENT PAGE
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/page/<path:page>'''], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def event_page(self, event, page, **post):
        values = {
            'event': event,
            'event_page': True,
        }

        base_page_name = page
        if '.' not in page:
            page = 'website_event.%s' % page

        view = request.env["website.event.menu"].sudo().search([
            ("event_id", "=", event.id),
            '|',
              ("view_id.key", "ilike", page),
              ("view_id.key", "ilike", f'website_event.{event.name}-{base_page_name.split("/")[-1]}'),
        ], limit=1).view_id

        try:
            # Every event page view should have its own SEO.
            page = view.key if view else page
            values['seo_object'] = request.website.get_template(page)
            values['main_object'] = event
        except ValueError:
            # page not found
            page = 'website.page_404'

        return request.render(page, values)

    @http.route(['''/event/<model("event.event"):event>'''], type='http', auth="public", website=True, sitemap=True, readonly=True)
    def event(self, event, **post):
        if event.menu_id and event.menu_id.child_id:
            target_url = event.menu_id.child_id[0].url
        else:
            target_url = '/event/%s/register' % str(event.id)
        if post.get('enable_editor') == '1':
            target_url += '?enable_editor=1'
        return request.redirect(target_url)

    @http.route(['''/event/<model("event.event"):event>/register'''], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def event_register(self, event, **post):
        values = self._prepare_event_register_values(event, **post)
        return request.render("website_event.event_description_full", values)

    def _prepare_event_register_values(self, event, **post):
        """Return the require values to render the template."""
        urls = lazy(event._get_event_resource_urls)
        return {
            'event': event,
            'slots': event.event_slot_ids.filtered(
                        lambda s: s.start_datetime > datetime.now()
                        and any(
                            availability is None or availability > 0
                            for availability in event._get_seats_availability([
                                (s, ticket) for ticket in event.event_ticket_ids or [False]
                            ])
                        )
                    ).grouped('date'),
            'main_object': event,
            'range': range,
            'google_url': lazy(lambda: urls.get('google_url')),
            'iCal_url': lazy(lambda: urls.get('iCal_url')),
            'registration_error_code': post.get('registration_error_code'),
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

    def _process_tickets_form(self, event, form_details):
        """ Process posted data about ticket order. Generic ticket are supported
        for event without tickets (generic registration).

        :return: list of order per ticket: [{
            'id': if of ticket if any (0 if no ticket),
            'ticket': browse record of ticket if any (None if no ticket),
            'name': ticket name (or generic 'Registration' name if no ticket),
            'quantity': number of registrations for that ticket,
            'current_limit_per_order': maximum of ticket orderable
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

        tickets = request.env['event.event.ticket'].browse(ticket_dict.keys())
        slot = request.env['event.slot'].browse(int(slot)) if (slot := form_details.get("event_slot_id", False)) else slot
        tickets_limits = tickets._get_current_limit_per_order(slot, event)

        return [{
            'id': tid if ticket_dict.get(tid) else 0,
            'ticket': ticket_dict.get(tid),
            'name': ticket_dict[tid]['name'] if ticket_dict.get(tid) else _('Registration'),
            'quantity': count,
            'current_limit_per_order': tickets_limits.get(tid, next(iter(tickets_limits.values()))),  # next is used if the ticket id isn't known (alone event case)
        } for tid, count in ticket_order.items() if count]

    @http.route(['/event/<model("event.event"):event>/registration/slot/<int:slot_id>/tickets'], type='jsonrpc', auth="public", methods=['POST'], website=True)
    def registration_tickets(self, event, slot_id):
        """ After slot selection, render ticket selection modal.
        To restrict the selectable number of tickets, give the slot seats available and
        each slot tickets seats available to the template.
        """
        slot = request.env['event.slot'].browse(slot_id)
        slot_tickets = [
            (slot, ticket)
            for ticket in event.event_ticket_ids
        ]
        return request.env['ir.ui.view']._render_template("website_event.modal_ticket_registration", {
            'event': event,
            'event_slot': slot,
            'seats_available_slot_tickets': {
                ticket.id: availability
                for (_, ticket), availability in zip(slot_tickets, event._get_seats_availability(slot_tickets))
            }
        })

    @http.route(['/event/<model("event.event"):event>/registration/new'], type='jsonrpc', auth="public", methods=['POST'], website=True)
    def registration_new(self, event, **post):
        """ After (slot and) tickets selection, render attendee(s) registration form.
        Slot and tickets availability check already performed in the template. """
        tickets = self._process_tickets_form(event, post)
        slot_id = post.get('event_slot_id', False)
        # Availability check needed as the total number of tickets can exceed the event/slot available tickets
        availability_check = True
        # Double check to verify that we are ordering fewer tickets than the limit conditions set
        limit_check = not any(ticket['quantity'] > ticket['current_limit_per_order'] for ticket in tickets)
        if event.seats_limited:
            ordered_seats = 0
            for ticket in tickets:
                ordered_seats += ticket['quantity']
            seats_available = event.seats_available
            if slot_id:
                seats_available = request.env['event.slot'].browse(int(slot_id)).seats_available or 0
            if seats_available < ordered_seats:
                availability_check = False
        if not tickets:
            return False
        default_first_attendee = {}
        if not request.env.user._is_public():
            default_first_attendee = {
                "name": request.env.user.name,
                "email": request.env.user.email,
                "phone": request.env.user.phone,
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_first_attendee = {
                    "name": visitor.display_name,
                    "email": visitor.email,
                    "phone": visitor.mobile,
                }
        return request.env['ir.ui.view']._render_template("website_event.registration_attendee_details", {
            'tickets': tickets,
            'event_slot_id': slot_id,
            'event': event,
            'availability_check': availability_check,
            'default_first_attendee': default_first_attendee,
            'limit_check': limit_check,
        })

    def _process_attendees_form(self, event, form_details):
        """ Process data posted from the attendee details form.
        Extracts question answers:
        - For both questions asked 'once_per_order' and questions asked to every attendee
        - For questions of type 'simple_choice', extracting the suggested answer id
        - For questions of type 'text_box', extracting the text answer of the attendee.

        :param form_details: posted data from frontend registration form, like
            {'1-name': 'r', '1-email': 'r@r.com', '1-phone': '', '1-event_slot_id': '1', '1-event_ticket_id': '1'}
        """
        allowed_fields = request.env['event.registration']._get_website_registration_allowed_fields()
        registration_fields = {key: v for key, v in request.env['event.registration']._fields.items() if key in allowed_fields}
        for ticket_id in list(filter(lambda x: x is not None, [form_details[field] if 'event_ticket_id' in field else None for field in form_details.keys()])):
            if int(ticket_id) not in event.event_ticket_ids.ids and len(event.event_ticket_ids.ids) > 0:
                raise UserError(_("This ticket is not available for sale for this event"))
        registrations = {}
        general_answer_ids = []
        general_identification_answers = {}
        # as we may have several questions populating the same field (e.g: the phone)
        # we use this to hold the fields that have already been handled
        # goal is to use the answer to the first question of every 'type' (aka name / phone / email / company name)
        already_handled_fields_data = {}
        for key, value in form_details.items():
            if not value or '-' not in key:
                continue

            key_values = key.split('-')
            # Special case for handling event_ticket_id data that holds only 2 values
            if len(key_values) == 2:
                registration_index, field_name = key_values
                if field_name not in registration_fields:
                    continue
                registrations.setdefault(registration_index, dict())[field_name] = int(value) or False
                continue

            if len(key_values) != 3:
                continue

            registration_index, question_type, question_id = key_values
            answer_values = None
            if question_type == 'simple_choice':
                answer_values = {
                    'question_id': int(question_id),
                    'value_answer_id': int(value)
                }
            else:
                answer_values = {
                    'question_id': int(question_id),
                    'value_text_box': value
                }

            if answer_values and not int(registration_index):
                general_answer_ids.append((0, 0, answer_values))
            elif answer_values:
                registrations.setdefault(registration_index, dict())\
                    .setdefault('registration_answer_ids', list()).append((0, 0, answer_values))

            if question_type in ('name', 'email', 'phone', 'company_name')\
                and question_type not in already_handled_fields_data.get(registration_index, []):
                if question_type not in registration_fields:
                    continue

                field_name = question_type
                already_handled_fields_data.setdefault(registration_index, list()).append(field_name)

                if not int(registration_index):
                    general_identification_answers[field_name] = value
                else:
                    registrations.setdefault(registration_index, dict())[field_name] = value

        if general_answer_ids:
            for registration in registrations.values():
                registration.setdefault('registration_answer_ids', list()).extend(general_answer_ids)

        if general_identification_answers:
            for registration in registrations.values():
                registration.update(general_identification_answers)

        return list(registrations.values())

    def _create_attendees_from_registration_post(self, event, registration_data):
        """ Also try to set a visitor (from request) and
        a partner (if visitor linked to a user for example). Purpose is to gather
        as much informations as possible, notably to ease future communications.
        Also try to update visitor informations based on registration info. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)

        registrations_to_create = []
        for registration_values in registration_data:
            registration_values['event_id'] = event.id
            if not registration_values.get('partner_id') and visitor_sudo.partner_id:
                registration_values['partner_id'] = visitor_sudo.partner_id.id
            elif not registration_values.get('partner_id'):
                registration_values['partner_id'] = False if request.env.user._is_public() else request.env.user.partner_id.id

            # update registration based on visitor
            registration_values['visitor_id'] = visitor_sudo.id

            registrations_to_create.append(registration_values)

        return request.env['event.registration'].sudo().create(registrations_to_create)

    @http.route(['''/event/<model("event.event"):event>/registration/confirm'''], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        """ Check before creating and finalize the creation of the registrations
            that we have enough seats for all selected tickets.
            If we don't, the user is instead redirected to page to register with a
            formatted error message. """
        try:
            request.env['ir.http']._verify_request_recaptcha_token('website_event_registration')
        except UserError:
            return request.redirect('/event/%s/register?registration_error_code=recaptcha_failed' % event.id)
        registrations_data = self._process_attendees_form(event, post)
        counter_per_combination = Counter((registration.get('event_slot_id', False), registration['event_ticket_id']) for registration in registrations_data)
        slot_ids = {slot_id for slot_id, _ in counter_per_combination if slot_id}
        ticket_ids = {ticket_id for _, ticket_id in counter_per_combination if ticket_id}
        slots_per_id = {slot.id: slot for slot in self.env['event.slot'].browse(slot_ids)}
        tickets_per_id = {ticket.id: ticket for ticket in self.env['event.event.ticket'].browse(ticket_ids)}
        try:
            event._verify_seats_availability(list({
                (slots_per_id.get(slot_id, False), tickets_per_id.get(ticket_id, False), count)
                for (slot_id, ticket_id), count in counter_per_combination.items()
            }))
        except ValidationError:
            return request.redirect('/event/%s/register?registration_error_code=insufficient_seats' % event.id)
        attendees_sudo = self._create_attendees_from_registration_post(event, registrations_data)

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
        slot = attendees_sudo.event_slot_id
        urls = event._get_event_resource_urls(slot)
        return {
            'attendees': attendees_sudo,
            'event': event,
            'google_url': urls.get('google_url'),
            'iCal_url': urls.get('iCal_url'),
            'slot': slot,
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

    # ------------------------------------------------------------
    # TOOLS (HELPERS)
    # ------------------------------------------------------------

    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('abbreviated', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s%s') % (month, start_date.strftime("%e"), (end_date != start_date and ("-" + end_date.strftime("%e")) or ""))

    def _extract_searched_event_tags(self, searches, slug_tags):
        tags = request.env['event.tag']
        if slug_tags:
            tags = self._event_search_tags_slug(slug_tags)
        elif 'tags' in searches:
            tags = self._event_search_tags_ids(searches['tags'])
        return tags

    def _slugify_tags(self, tag_ids, toggle_tag_id=None):
        """ Prepares a comma separated slugified tags for the sake of readable URLs.

        :param toggle_tag_id: add the tag being clicked to the already
          selected tags as well as in URL; if tag is already selected
          by the user it is removed from the selected tags (and so from the URL);
        """
        tag_ids = list(tag_ids)
        if toggle_tag_id and toggle_tag_id in tag_ids:
            tag_ids.remove(toggle_tag_id)
        elif toggle_tag_id:
            tag_ids.append(toggle_tag_id)

        return ','.join(request.env['ir.http']._slug(tag_id) for tag_id in request.env['event.tag'].browse(tag_ids)) or ''

    def _event_search_tags_ids(self, search_tags):
        """ Input: %5B4%5D """
        EventTag = request.env['event.tag']
        try:
            tag_ids = literal_eval(search_tags or '')
        except Exception:  # noqa: BLE001
            return EventTag

        return EventTag.search([('id', 'in', tag_ids)]) if tag_ids else EventTag

    def _event_search_tags_slug(self, search_tags):
        """ Input: event-1,event-2 """
        EventTag = request.env['event.tag']
        try:
            tag_ids = list(filter(None, [request.env['ir.http']._unslug(tag)[1] for tag in (search_tags or '').split(',')]))
        except Exception:  # noqa: BLE001
            return EventTag

        return EventTag.search([('id', 'in', tag_ids)]) if tag_ids else EventTag

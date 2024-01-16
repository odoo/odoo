# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import json
import werkzeug.urls

from pytz import utc

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv import expression
from odoo.tools.misc import get_lang, format_date

GOOGLE_CALENDAR_URL = 'https://www.google.com/calendar/render?'


class Event(models.Model):
    _name = 'event.event'
    _inherit = [
        'event.event',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.cover_properties.mixin',
        'website.searchable.mixin',
    ]

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res.update({
            'background-image': "url('/website_event/static/src/img/event_cover_4.jpg')",
            'opacity': '0.4',
            'resize_class': 'cover_auto'
        })
        return res

    # description
    subtitle = fields.Char('Event Subtitle', translate=True)
    # registration
    is_participating = fields.Boolean("Is Participating", compute="_compute_is_participating")
    # website
    website_published = fields.Boolean(tracking=True)
    website_menu = fields.Boolean(
        string='Website Menu',
        compute='_compute_website_menu', readonly=False, store=True,
        help="Allows to display and manage event-specific menus on website.")
    menu_id = fields.Many2one('website.menu', 'Event Menu', copy=False)
    menu_register_cta = fields.Boolean(
        'Extra Register Button', compute='_compute_menu_register_cta',
        readonly=False, store=True)
    # sub-menus management
    introduction_menu = fields.Boolean(
        "Introduction Menu", compute="_compute_website_menu_data",
        readonly=False, store=True)
    introduction_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Introduction Menus",
        domain=[("menu_type", "=", "introduction")])
    location_menu = fields.Boolean(
        "Location Menu", compute="_compute_website_menu_data",
        readonly=False, store=True)
    location_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Location Menus",
        domain=[("menu_type", "=", "location_menu")])
    register_menu = fields.Boolean(
        "Register Menu", compute="_compute_website_menu_data",
        readonly=False, store=True)
    register_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Register Menus",
        domain=[("menu_type", "=", "register")])
    community_menu = fields.Boolean(
        "Community Menu", compute="_compute_community_menu",
        readonly=False, store=True,
        help="Display community tab on website")
    community_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Event Community Menus",
        domain=[("menu_type", "=", "community")])
    # live information
    is_ongoing = fields.Boolean(
        'Is Ongoing', compute='_compute_time_data', search='_search_is_ongoing',
        help="Whether event has begun")
    is_done = fields.Boolean(
        'Is Done', compute='_compute_time_data',
        help="Whether event is finished")
    start_today = fields.Boolean(
        'Start Today', compute='_compute_time_data',
        help="Whether event is going to start today if still not ongoing")
    start_remaining = fields.Integer(
        'Remaining before start', compute='_compute_time_data',
        help="Remaining time before event starts (minutes)")

    def _compute_is_participating(self):
        """Heuristic

          * public, no visitor: not participating as we have no information;
          * public and visitor: check visitor is linked to a registration. As
            visitors are merged on the top parent, current visitor check is
            sufficient even for successive visits;
          * logged, no visitor: check partner is linked to a registration. Do
            not check the email as it is not really secure;
          * logged as visitor: check partner or visitor are linked to a
            registration;
        """
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            events = self.env['event.event']
        elif self.env.user._is_public():
            events = self.env['event.registration'].sudo().search([
                ('event_id', 'in', self.ids),
                ('state', '!=', 'cancel'),
                ('visitor_id', '=', current_visitor.id),
            ]).event_id
        else:
            if current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]
            events = self.env['event.registration'].sudo().search(
                expression.AND([
                    domain,
                    ['&', ('event_id', 'in', self.ids), ('state', '!=', 'cancel')]
                ])
            ).event_id

        for event in self:
            event.is_participating = event in events

    @api.depends('event_type_id')
    def _compute_website_menu(self):
        """ Also ensure a value for website_menu as it is a trigger notably for
        track related menus. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_menu = event.event_type_id.website_menu
            elif not event.website_menu:
                event.website_menu = False

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        """ Set False in base module. Sub modules will add their own logic
        (meet or track_quiz). """
        for event in self:
            event.community_menu = False

    @api.depends("website_menu")
    def _compute_website_menu_data(self):
        """ Synchronize with website_menu at change and let people update them
        at will afterwards. """
        for event in self:
            event.introduction_menu = event.website_menu
            event.location_menu = event.website_menu
            event.register_menu = event.website_menu

    @api.depends("event_type_id", "website_menu")
    def _compute_menu_register_cta(self):
        """ At type onchange: synchronize. At website_menu update: synchronize. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.menu_register_cta = event.event_type_id.menu_register_cta
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.menu_register_cta):
                event.menu_register_cta = True
            elif not event.website_menu:
                event.menu_register_cta = False

    @api.depends('date_begin', 'date_end')
    def _compute_time_data(self):
        """ Compute start and remaining time. Do everything in UTC as we compute only
        time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for event in self:
            date_begin_utc = utc.localize(event.date_begin, is_dst=False)
            date_end_utc = utc.localize(event.date_end, is_dst=False)
            event.is_ongoing = date_begin_utc <= now_utc <= date_end_utc
            event.is_done = now_utc > date_end_utc
            event.start_today = date_begin_utc.date() == now_utc.date()
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                event.start_remaining = int(td.total_seconds() / 60)
            else:
                event.start_remaining = 0

    @api.depends('name')
    def _compute_website_url(self):
        super(Event, self)._compute_website_url()
        for event in self:
            if event.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                event.website_url = '/event/%s' % slug(event)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        events._update_website_menus()
        return events

    def write(self, vals):
        menus_state_by_field = self._split_menus_state_by_field()
        res = super(Event, self).write(vals)
        menus_update_by_field = self._get_menus_update_by_field(menus_state_by_field, force_update=vals.keys())
        self._update_website_menus(menus_update_by_field=menus_update_by_field)
        return res

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_website_menu(self, val):
        self.website_menu = val

    def _get_menu_update_fields(self):
        """" Return a list of fields triggering a split of menu to activate /
        menu to de-activate. Due to saas-13.3 improvement of menu management
        this is done using side-methods to ease inheritance.

        :return list: list of fields, each of which triggering a menu update
          like website_menu, website_track, ... """
        return ['community_menu', 'introduction_menu', 'location_menu', 'register_menu']

    def _get_menu_type_field_matching(self):
        return {
            'community': 'community_menu',
            'introduction': 'introduction_menu',
            'location': 'location_menu',
            'register': 'register_menu',
        }

    def _split_menus_state_by_field(self):
        """ For each field linked to a menu, get the set of events having this
        menu activated and de-activated. Purpose is to find those whose value
        changed and update the underlying menus.

        :return dict: key = name of field triggering a website menu update, get {
          'activated': subset of self having its menu currently set to True
          'deactivated': subset of self having its menu currently set to False
        } """
        menus_state_by_field = dict()
        for fname in self._get_menu_update_fields():
            activated = self.filtered(lambda event: event[fname])
            menus_state_by_field[fname] = {
                'activated': activated,
                'deactivated': self - activated,
            }
        return menus_state_by_field

    def _get_menus_update_by_field(self, menus_state_by_field, force_update=None):
        """ For each field linked to a menu, get the set of events requiring
        this menu to be activated or de-activated based on previous recorded
        value.

        :param menus_state_by_field: see ``_split_menus_state_by_field``;
        :param force_update: list of field to which we force update of menus. This
          is used notably when a direct write to a stored editable field messes with
          its pre-computed value, notably in a transient mode (aka demo for example);

        :return dict: key = name of field triggering a website menu update, get {
          'activated': subset of self having its menu toggled to True
          'deactivated': subset of self having its menu toggled to False
        } """
        menus_update_by_field = dict()
        for fname in self._get_menu_update_fields():
            if fname in force_update:
                menus_update_by_field[fname] = self
            else:
                menus_update_by_field[fname] = self.env['event.event']
                menus_update_by_field[fname] |= menus_state_by_field[fname]['activated'].filtered(lambda event: not event[fname])
                menus_update_by_field[fname] |= menus_state_by_field[fname]['deactivated'].filtered(lambda event: event[fname])
        return menus_update_by_field

    def _get_website_menu_entries(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules.

        Each menu entry is a tuple containing :
          * name: menu item name
          * url: if set, url to a route (do not use xml_id in that case);
          * xml_id: template linked to the page (do not use url in that case);
          * sequence: specific sequence of menu entry to be set on the menu;
          * menu_type: type of menu entry (used in inheriting modules to ease
            menu management; not used in this module in 13.3 due to technical
            limitations);
        """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro', 1, 'introduction'),
            (_('Location'), False, 'website_event.template_location', 50, 'location'),
            (_('Register'), '/event/%s/register' % slug(self), False, 100, 'register'),
            (_('Community'), '/event/%s/community' % slug(self), False, 80, 'community'),
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        """ Synchronize event configuration and its menu entries for frontend.

        :param menus_update_by_field: see ``_get_menus_update_by_field``"""
        for event in self:
            if event.menu_id and not event.website_menu:
                # do not rely on cascade, as it is done in SQL -> not calling override and
                # letting some ir.ui.views in DB
                (event.menu_id + event.menu_id.child_id).sudo().unlink()
            elif event.website_menu and not event.menu_id:
                root_menu = self.env['website.menu'].sudo().create({'name': event.name, 'website_id': event.website_id.id})
                event.menu_id = root_menu
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('community_menu')):
                event._update_website_menu_entry('community_menu', 'community_menu_ids', 'community')
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('introduction_menu')):
                event._update_website_menu_entry('introduction_menu', 'introduction_menu_ids', 'introduction')
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('location_menu')):
                event._update_website_menu_entry('location_menu', 'location_menu_ids', 'location')
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('register_menu')):
                event._update_website_menu_entry('register_menu', 'register_menu_ids', 'register')

    def _update_website_menu_entry(self, fname_bool, fname_o2m, fmenu_type):
        """ Generic method to create menu entries based on a flag on event. This
        method is a bit obscure, but is due to preparation of adding new menus
        entries and pages for event in a stable version, leading to some constraints
        while developing.

        :param fname_bool: field name (e.g. website_track)
        :param fname_o2m: o2m linking towards website.event.menu matching the
          boolean fields (normally an entry ot website.event.menu with type matching
          the boolean field name)
        :param method_name: method returning menu entries information: url, sequence, ...
        """
        self.ensure_one()
        new_menu = None

        menu_data = [menu_info for menu_info in self._get_website_menu_entries()
                     if menu_info[4] == fmenu_type]
        if self[fname_bool] and not self[fname_o2m]:
            # menus not found but boolean True: get menus to create
            for name, url, xml_id, menu_sequence, menu_type in menu_data:
                new_menu = self._create_menu(menu_sequence, name, url, xml_id, menu_type)
        elif not self[fname_bool]:
            # will cascade delete to the website.event.menu
            self[fname_o2m].mapped('menu_id').sudo().unlink()

        return new_menu

    def _create_menu(self, sequence, name, url, xml_id, menu_type):
        """ Create a new menu for the current event.

        If url: create a website menu. Menu leads directly to the URL that
        should be a valid route.

        If xml_id: create a new page using the qweb template given by its
        xml_id. Take its url back thanks to new_page of website, then link
        it to a menu. Template is duplicated and linked to a new url, meaning
        each menu will have its own copy of the template. This is currently
        limited to two menus: introduction and location.

        :param menu_type: type of menu. Mainly used for inheritance purpose
          allowing more fine-grain tuning of menus.
        """
        self.check_access_rights('write')
        view_id = False
        if not url:
            # add_menu=False, ispage=False -> simply create a new ir.ui.view with name
            # and template
            page_result = self.env['website'].sudo().new_page(
                name=name + ' ' + self.name, template=xml_id,
                add_menu=False, ispage=False)
            url = "/event/" + slug(self) + "/page" + page_result['url']  # url contains starting "/"
            view_id = page_result['view_id']

        website_menu = self.env['website.menu'].sudo().create({
            'name': name,
            'url': url,
            'parent_id': self.menu_id.id,
            'sequence': sequence,
            'website_id': self.website_id.id,
        })
        self.env['website.event.menu'].create({
            'menu_id': website_menu.id,
            'event_id': self.id,
            'menu_type': menu_type,
            'view_id': view_id,
        })
        return website_menu

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def google_map_link(self, zoom=8):
        """ Temporary method for stable """
        return self._google_map_link(zoom=zoom)

    def _google_map_link(self, zoom=8):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_link(zoom=zoom)
        return None

    def _track_subtype(self, init_values):
        self.ensure_one()
        if init_values.keys() & {'is_published', 'website_published'}:
            if self.is_published:
                return self.env.ref('website_event.mt_event_published', raise_if_not_found=False)
            return self.env.ref('website_event.mt_event_unpublished', raise_if_not_found=False)
        return super(Event, self)._track_subtype(init_values)

    def _get_event_resource_urls(self):
        url_date_start = self.date_begin.strftime('%Y%m%dT%H%M%SZ')
        url_date_stop = self.date_end.strftime('%Y%m%dT%H%M%SZ')
        params = {
            'action': 'TEMPLATE',
            'text': self.name,
            'dates': url_date_start + '/' + url_date_stop,
            'details': self.name,
        }
        if self.address_id:
            params.update(location=self.sudo().address_id.contact_address.replace('\n', ' '))
        encoded_params = werkzeug.urls.url_encode(params)
        google_url = GOOGLE_CALENDAR_URL + encoded_params
        iCal_url = '/event/%d/ics?%s' % (self.id, encoded_params)
        return {'google_url': google_url, 'iCal_url': iCal_url}

    def _default_website_meta(self):
        res = super(Event, self)._default_website_meta()
        event_cover_properties = json.loads(self.cover_properties)
        # background-image might contain single quotes eg `url('/my/url')`
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = event_cover_properties.get('background-image', 'none')[4:-1].strip("'")
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.subtitle
        res['default_twitter']['twitter:card'] = 'summary'
        res['default_meta_description'] = self.subtitle
        return res

    def get_backend_menu_id(self):
        return self.env.ref('event.event_main_menu').id

    @api.model
    def _search_build_dates(self):
        today = fields.Datetime.today()

        def sdn(date):
            return fields.Datetime.to_string(date.replace(hour=23, minute=59, second=59))

        def sd(date):
            return fields.Datetime.to_string(date)

        def get_month_filter_domain(filter_name, months_delta):
            first_day_of_the_month = today.replace(day=1)
            filter_string = _('This month') if months_delta == 0 \
                else format_date(self.env, value=today + relativedelta(months=months_delta),
                    date_format='LLLL', lang_code=get_lang(self.env).code).capitalize()
            return [filter_name, filter_string, [
                ("date_end", ">=", sd(first_day_of_the_month + relativedelta(months=months_delta))),
                ("date_begin", "<", sd(first_day_of_the_month + relativedelta(months=months_delta+1)))],
                0]

        return [
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

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        with_date = options['displayDetail']
        date = options.get('date', 'all')
        country = options.get('country')
        tags = options.get('tags')
        event_type = options.get('type', 'all')

        domain = [website.website_domain()]
        if event_type != 'all':
            domain.append([("event_type_id", "=", int(event_type))])
        search_tags = self.env['event.tag']
        if tags:
            try:
                tag_ids = literal_eval(tags)
            except SyntaxError:
                pass
            else:
                # perform a search to filter on existing / valid tags implicitely + apply rules on color
                search_tags = self.env['event.tag'].search([('id', 'in', tag_ids)])

            # Example: You filter on age: 10-12 and activity: football.
            # Doing it this way allows to only get events who are tagged "age: 10-12" AND "activity: football".
            # Add another tag "age: 12-15" to the search and it would fetch the ones who are tagged:
            # ("age: 10-12" OR "age: 12-15") AND "activity: football
            grouped_tags = defaultdict(list)
            for tag in search_tags:
                grouped_tags[tag.category_id].append(tag)
            for group in grouped_tags:
                domain.append([('tag_ids', 'in', [tag.id for tag in grouped_tags[group]])])

        no_country_domain = domain.copy()
        if country:
            if country == 'online':
                domain.append([("country_id", "=", False)])
            elif country != 'all':
                domain.append(['|', ("country_id", "=", int(country)), ("country_id", "=", False)])

        no_date_domain = domain.copy()
        dates = self._search_build_dates()
        current_date = None
        for date_details in dates:
            if date == date_details[0]:
                domain.append(date_details[2])
                no_country_domain.append(date_details[2])
                if date_details[0] != 'all':
                    current_date = date_details[1]

        search_fields = ['name']
        fetch_fields = ['name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('subtitle')
            fetch_fields.append('subtitle')
            mapping['description'] = {'name': 'subtitle', 'type': 'text', 'match': True}
        if with_date:
            mapping['detail'] = {'name': 'range', 'type': 'html'}
        return {
            'model': 'event.event',
            'base_domain': domain,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-ticket',
            # for website_event main controller:
            'dates': dates,
            'current_date': current_date,
            'search_tags': search_tags,
            'no_date_domain': no_date_domain,
            'no_country_domain': no_country_domain,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_date = 'detail' in mapping
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        if with_date:
            for event, data in zip(self, results_data):
                begin = self.env['ir.qweb.field.date'].record_to_html(event, 'date_begin', {})
                end = self.env['ir.qweb.field.date'].record_to_html(event, 'date_end', {})
                data['range'] = '%s🠖%s' % (begin, end) if begin != end else begin
        return results_data

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug.urls

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug

GOOGLE_CALENDAR_URL = 'https://www.google.com/calendar/render?'


class Event(models.Model):
    _name = 'event.event'
    _inherit = [
        'event.event',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.cover_properties.mixin'
    ]

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res['opacity'] = '0.4'
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
        help="Creates menus Introduction, Location and Register on the page "
             "of the event on the website.")
    menu_id = fields.Many2one('website.menu', 'Event Menu', copy=False)

    def _compute_is_participating(self):
        # we don't allow public user to see participating label
        if self.env.user != self.env['website'].get_current_website().user_id:
            email = self.env.user.partner_id.email
            for event in self:
                domain = ['&', '|', ('email', '=', email), ('partner_id', '=', self.env.user.partner_id.id), ('event_id', '=', event.id)]
                event.is_participating = self.env['event.registration'].sudo().search_count(domain)
        else:
            self.is_participating = False

    @api.depends('name')
    def _compute_website_url(self):
        super(Event, self)._compute_website_url()
        for event in self:
            if event.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                event.website_url = '/event/%s' % slug(event)

    @api.depends('event_type_id')
    def _compute_website_menu(self):
        """ Also ensure a value for website_menu as it is a trigger notably for
        track related menus. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_menu = event.event_type_id.website_menu
            elif not event.website_menu:
                event.website_menu = False

    @api.model
    def create(self, vals):
        res = super(Event, self).create(vals)
        res._update_website_menus()
        return res

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
        return ['website_menu']

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

    def _get_menu_entries(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules.

        Each menu entry is a tuple containing :
          * name: menu item name
          * url: if set, url to a route (do not use xml_id in that case);
          * xml_id: template linked to the page (do not use url in that case);
        """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro'),
            (_('Location'), False, 'website_event.template_location'),
            (_('Register'), '/event/%s/register' % slug(self), False),
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        """ Synchronize event configuration and its menu entries for frontend.

        :param menus_update_by_field: see ``_get_menus_update_by_field``"""
        for event in self:
            if event.menu_id and not event.website_menu:
                event.menu_id.sudo().unlink()
            elif event.website_menu and not event.menu_id:
                root_menu = self.env['website.menu'].sudo().create({'name': event.name, 'website_id': event.website_id.id})
                event.menu_id = root_menu
                for sequence, (name, url, xml_id) in enumerate(event._get_menu_entries()):
                    event._create_menu(sequence, name, url, xml_id)

    def _create_menu(self, sequence, name, url, xml_id, menu_type=False):
        """ If url: create a website menu. Menu leads directly to the URL that
        should be a valid route. If xml_id: create a new page, take its url back
        thanks to new_page of website, then link it to a menu. Template is
        duplicated and linked to a new url, meaning each menu will have its own
        copy of the template.

        :param menu_type: type of menu. Mainly used for inheritance purpose
          allowing more fine-grain tuning of menus. """
        if not url:
            self.env['ir.ui.view'].with_context(_force_unlink=True).search([('name', '=', name + ' ' + self.name)]).unlink()
            page_result = self.env['website'].sudo().new_page(name + ' ' + self.name, template=xml_id, ispage=False)
            url = "/event/" + slug(self) + "/page" + page_result['url']  # url contains starting "/"
        website_menu = self.env['website.menu'].sudo().create({
            'name': name,
            'url': url,
            'parent_id': self.menu_id.id,
            'sequence': sequence,
            'website_id': self.website_id.id,
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
        if 'is_published' in init_values and self.is_published:
            return self.env.ref('website_event.mt_event_published')
        elif 'is_published' in init_values and not self.is_published:
            return self.env.ref('website_event.mt_event_unpublished')
        return super(Event, self)._track_subtype(init_values)

    def action_open_badge_editor(self):
        """ open the event badge editor : redirect to the report page of event badge report """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/report/html/%s/%s?enable_editor' % ('event.event_event_report_template_badge', self.id),
        }

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

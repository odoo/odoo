# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls
import json

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug

GOOGLE_CALENDAR_URL = 'https://www.google.com/calendar/render?'


class EventType(models.Model):
    _name = 'event.type'
    _inherit = ['event.type']

    website_menu = fields.Boolean('Display a dedicated menu on Website')


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'website.seo.metadata', 'website.published.multi.mixin', 'website.cover_properties.mixin']

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
                event.is_participating = self.env['event.registration'].search_count(domain)
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
        split_tocheck = self._split_for_menu_update()
        res = super(Event, self).write(vals)
        split_to_update = self._get_events_for_menu_update(split_tocheck)
        self._update_website_menus(split_to_update=split_to_update)
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

    def _split_for_menu_update(self):
        """ For each field linked to a menu, get the set of events having this
        menu activated and de-activated. Purpose is to find those whose value
        changed and update the underlying menus. """
        split_tocheck = dict()
        for fname in self._get_menu_update_fields():
            activated = self.filtered(lambda event: event[fname])
            split_tocheck[fname] = {
                'activated': activated,
                'deactivated': self - activated,
            }
        return split_tocheck

    def _get_events_for_menu_update(self, split_result):
        """ For each field linked to a menu, get the set of events requiring
        this menu to be activated or de-activated based on previous recorded
        value. """
        split_to_update = dict()
        for fname in self._get_menu_update_fields():
            split_to_update[fname] = self.env['event.event']
            split_to_update[fname] |= split_result[fname]['activated'].filtered(lambda event: not event[fname])
            split_to_update[fname] |= split_result[fname]['deactivated'].filtered(lambda event: event[fname])
        return split_to_update

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

    def _update_website_menus(self, split_to_update=None):
        """ Synchronize event configuration and its menu entries for frontend. """
        for event in self:
            if event.menu_id and not event.website_menu:
                event.menu_id.unlink()
            elif event.website_menu and not event.menu_id:
                root_menu = self.env['website.menu'].sudo().create({'name': event.name, 'website_id': event.website_id.id})
                event.menu_id = root_menu
                for sequence, (name, url, xml_id) in enumerate(event._get_menu_entries()):
                    event._create_menu(sequence, name, url, xml_id)

    def _create_menu(self, sequence, name, url, xml_id, menu_type=False, force_track=False):
        """ If url: create a website menu. Tracking visitors is decided on the
        template used by this route. If xml_id: create a new page, then link
        it to a menu.

        :param menu_type: type of menu. Mainly used for inheritance purpose
          allowing more fine-grain tuning of menus. """
        if not url:
            self.env['ir.ui.view'].search([('name', '=', name + ' ' + self.name)]).unlink()
            newpath = self.env['website'].sudo().new_page(name + ' ' + self.name, template=xml_id, ispage=False, force_track=force_track)['url']
            url = "/event/" + slug(self) + "/page/" + newpath[1:]
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

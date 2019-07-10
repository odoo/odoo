# -*- coding: utf-8 -*-

import pytz
import werkzeug

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError

GOOGLE_CALENDAR_URL = 'https://www.google.com/calendar/render?'


class EventType(models.Model):
    _name = 'event.type'
    _inherit = ['event.type']

    website_menu = fields.Boolean(
        'Display a dedicated menu on Website')


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'website.seo.metadata', 'website.published.multi.mixin']

    is_published = fields.Boolean(tracking=True)

    is_participating = fields.Boolean("Is Participating", compute="_compute_is_participating")

    website_menu = fields.Boolean('Dedicated Menu',
        help="Creates menus Introduction, Location and Register on the page "
             " of the event on the website.", copy=False)
    menu_id = fields.Many2one('website.menu', 'Event Menu', copy=False)

    def _compute_is_participating(self):
        # we don't allow public user to see participating label
        if self.env.user != self.env['website'].get_current_website().user_id:
            email = self.env.user.partner_id.email
            for event in self:
                domain = ['&', '|', ('email', '=', email), ('partner_id', '=', self.env.user.partner_id.id), ('event_id', '=', event.id)]
                event.is_participating = self.env['event.registration'].search_count(domain)

    @api.depends('name')
    def _compute_website_url(self):
        super(Event, self)._compute_website_url()
        for event in self:
            if event.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                event.website_url = '/event/%s' % slug(event)

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(Event, self)._onchange_type()
        if self.event_type_id:
            self.website_menu = self.event_type_id.website_menu

    def _get_menu_entries(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules. """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro'),
            (_('Location'), False, 'website_event.template_location'),
            (_('Register'), '/event/%s/register' % slug(self), False),
        ]

    def _toggle_create_website_menus(self, vals):
        for event in self:
            if 'website_menu' in vals:
                if event.menu_id and not event.website_menu:
                    event.menu_id.unlink()
                elif event.website_menu:
                    if not event.menu_id:
                        root_menu = self.env['website.menu'].create({'name': event.name, 'website_id': event.website_id.id})
                        event.menu_id = root_menu
                    for sequence, (name, url, xml_id) in enumerate(event._get_menu_entries()):
                        event._create_menu(sequence, name, url, xml_id)

    @api.model
    def create(self, vals):
        res = super(Event, self).create(vals)
        res._toggle_create_website_menus(vals)
        return res

    def write(self, vals):
        res = super(Event, self).write(vals)
        self._toggle_create_website_menus(vals)
        return res

    def _create_menu(self, sequence, name, url, xml_id):
        if not url:
            newpath = self.env['website'].new_page(name + ' ' + self.name, template=xml_id, ispage=False)['url']
            url = "/event/" + slug(self) + "/page/" + newpath[1:]
        menu = self.env['website.menu'].create({
            'name': name,
            'url': url,
            'parent_id': self.menu_id.id,
            'sequence': sequence,
            'website_id': self.website_id.id,
        })
        return menu

    def google_map_img(self, zoom=8, width=298, height=298):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_img(zoom=zoom, width=width, height=height)
        return None

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

    def _get_event_resource_urls(self, attendees):
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
        encoded_params = werkzeug.url_encode(params)
        google_url = GOOGLE_CALENDAR_URL + encoded_params
        iCal_url = '/event/%d/ics?%s' % (self.id, encoded_params)
        return {'google_url': google_url, 'iCal_url': iCal_url}

    def _default_website_meta(self):
        res = super(Event, self)._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.date_begin
        res['default_twitter']['twitter:card'] = 'summary'
        res['default_meta_description'] = self.date_begin
        return res

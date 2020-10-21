# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventType(models.Model):
    _inherit = 'event.type'

    website_booth = fields.Boolean(
        string='Booths on Website', compute='_compute_website_menu_data',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_website_menu_data(self):
        for event_type in self:
            event_type.website_booth = event_type.website_menu


class Event(models.Model):
    _inherit = 'event.event'

    exhibition_map = fields.Image(string='Exhibition Map', max_width=1024, max_height=1024)
    website_booth = fields.Boolean(
        string='Booths on Website', compute='_compute_website_booth',
        readonly=False, store=True)
    booth_menu_ids = fields.One2many(
        'website.event.menu', 'event_id',
        string='Event Booths Menus', domain=[('menu_type', '=', 'booth')])

    @api.depends('event_type_id', 'website_menu')
    def _compute_website_booth(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_booth = event.event_type_id.website_booth
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.website_booth):
                event.website_booth = True
            elif not event.website_menu:
                event.website_booth = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_website_booth(self, val):
        self.website_booth = val

    def _get_menu_update_fields(self):
        return super(Event, self)._get_menu_update_fields() + ['website_booth']

    def _update_website_menus(self, menus_update_by_field=None):
        super(Event, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('website_booth')):
                event._update_website_menu_entry('website_booth', 'booth_menu_ids', '_get_booth_menu_entries')

    def _get_menu_type_field_matching(self):
        res = super(Event, self)._get_menu_type_field_matching()
        res['booth'] = 'website_booth'
        return res

    def _get_booth_menu_entries(self):
        self.ensure_one()
        return [
            (_('Become a sponsor'), '/event/%s/booths/register' % slug(self), False, 90, 'booth')
        ]

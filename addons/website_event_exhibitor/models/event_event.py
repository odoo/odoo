# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    # sponsors
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    sponsor_count = fields.Integer('Sponsor Count', compute='_compute_sponsor_count')
    # frontend menu management
    exhibitor_menu = fields.Boolean(
        string='Showcase Exhibitors', compute='_compute_exhibitor_menu',
        readonly=False, store=True)
    exhibitor_menu_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Exhibitors Menus',
        domain=[('menu_type', '=', 'exhibitor')])

    def _compute_sponsor_count(self):
        data = self.env['event.sponsor']._read_group([], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.sponsor_count = result.get(event.id, 0)

    @api.depends('event_type_id', 'website_menu', 'exhibitor_menu')
    def _compute_exhibitor_menu(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.exhibitor_menu = event.event_type_id.exhibitor_menu
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.exhibitor_menu):
                event.exhibitor_menu = True
            elif not event.website_menu:
                event.exhibitor_menu = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_exhibitor_menu(self, val):
        self.exhibitor_menu = val

    def _get_menu_update_fields(self):
        return super(EventEvent, self)._get_menu_update_fields() + ['exhibitor_menu']

    def _update_website_menus(self, menus_update_by_field=None):
        super(EventEvent, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('exhibitor_menu')):
                event._update_website_menu_entry('exhibitor_menu', 'exhibitor_menu_ids', 'exhibitor')

    def _get_menu_type_field_matching(self):
        res = super(EventEvent, self)._get_menu_type_field_matching()
        res['exhibitor'] = 'exhibitor_menu'
        return res

    def _get_website_menu_entries(self):
        self.ensure_one()
        return super(EventEvent, self)._get_website_menu_entries() + [
            (_('Exhibitors'), '/event/%s/exhibitors' % slug(self), False, 60, 'exhibitor')
        ]

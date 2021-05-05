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
        data = self.env['event.sponsor'].read_group([], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.sponsor_count = result.get(event.id, 0)

    @api.depends('event_type_id', 'website_menu')
    def _compute_exhibitor_menu(self):
        for event in self:
            # If we activate website_menu and there is event_type, take event type value, unless exhibitor menu is already activated.
            if event.event_type_id and (event.event_type_id != event._origin.event_type_id) or (event.website_menu and not event.exhibitor_menu):
                event.exhibitor_menu = event.event_type_id.exhibitor_menu
            # If no event type, or if there is event type but exhibitor_menu is already set when setting website_menu, simply take same value as website_menu
            else:
                event.exhibitor_menu = event.website_menu

    @api.onchange('website_menu')
    def _onchange_website_menu(self):
        """use onchange to make sure that website_exhibitor has the correct value
           when the user makes changes inside the form, what we want is that when the
           user activates the menu the website_exhibitor field to be set to
           the value of the template, if the event is not linked to a template the value will
           be set to true. When the menu is deactivated it should always be false"""
        super(EventEvent, self)._onchange_website_menu()
        for event in self:
            if event.website_menu and event.event_type_id:
                event.exhibitor_menu = event.event_type_id.exhibitor_menu
            else:
                event.exhibitor_menu = event.website_menu

    @api.onchange('event_type_id')
    def _on_change_event_type(self):
        """use onchange to make sure that website_exhibitor has the correct value
        when the user makes changes inside the form"""
        super(EventEvent, self)._onchange_event_type()
        for event in self:
            if event.event_type_id:
                event.exhibitor_menu = event.event_type_id.exhibitor_menu

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_website_menu(self, val):
        super(EventEvent, self).toggle_website_menu(val)
        if val:
            if self.event_type_id:
                self.exhibitor_menu = self.event_type_id.exhibitor_menu
            else:
                self.exhibitor_menu = self.website_menu

    def toggle_exhibitor_menu(self, val):
        self.exhibitor_menu = val

    def _get_menu_update_fields(self):
        return super(EventEvent, self)._get_menu_update_fields() + ['exhibitor_menu']

    def _update_website_menus(self, menus_update_by_field=None):
        super(EventEvent, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('exhibitor_menu')):
                event._update_website_menu_entry('exhibitor_menu', 'exhibitor_menu_ids', '_get_exhibitor_menu_entries')

    def _get_menu_type_field_matching(self):
        res = super(EventEvent, self)._get_menu_type_field_matching()
        res['exhibitor'] = 'exhibitor_menu'
        return res

    def _get_exhibitor_menu_entries(self):
        self.ensure_one()
        return [(_('Exhibitors'), '/event/%s/exhibitors' % slug(self), False, 60, 'exhibitor')]

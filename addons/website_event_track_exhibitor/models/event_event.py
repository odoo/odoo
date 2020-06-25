# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    menu_exhibitor = fields.Boolean(
        string='Exhibitors on Website', compute='_compute_menu_exhibitor',
        readonly=False, store=True)
    menu_exhibitor_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Exhibitors Menus',
        domain=[('menu_type', '=', 'exhibitor')])

    @api.depends('event_type_id', 'website_menu', 'menu_exhibitor')
    def _compute_menu_exhibitor(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.menu_exhibitor = event.event_type_id.menu_exhibitor
            elif not event.website_menu or not event.menu_exhibitor:
                event.menu_exhibitor = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_menu_exhibitor(self, val):
        self.menu_exhibitor = val

    def _get_menu_update_fields(self):
        update_fields = super(EventEvent, self)._get_menu_update_fields()
        update_fields += ['menu_exhibitor']
        return update_fields

    def _update_website_menus(self, split_to_update=None):
        super(EventEvent, self)._update_website_menus(split_to_update=split_to_update)
        for event in self:
            if not split_to_update or event in split_to_update.get('menu_exhibitor'):
                event._update_website_menu_entry('menu_exhibitor', 'menu_exhibitor_ids', '_get_exhibitor_menu_entries')

    def _get_exhibitor_menu_entries(self):
        self.ensure_one()
        res = [(_('Exhibitors'), '/event/%s/exhibitors' % slug(self), False, 60, 'exhibitor', False)]
        return res

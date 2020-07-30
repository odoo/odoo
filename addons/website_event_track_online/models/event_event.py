# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    community_menu = fields.Boolean(
        "Community Menu", compute="_compute_community_menu",
        readonly=False, store=True,
        help="Display community tab on website")
    community_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Event Community Menus",
        domain=[("menu_type", "=", "community")])

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        """ At type onchange: synchronize. At website_menu update: synchronize. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.community_menu = event.event_type_id.community_menu
            elif event.website_menu and event.website_menu != event._origin.website_menu or not event.community_menu:
                event.community_menu = True
            elif not event.website_menu:
                event.community_menu = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    # OVERRIDES: ADD SEQUENCE

    def _get_menu_update_fields(self):
        update_fields = super(EventEvent, self)._get_menu_update_fields()
        update_fields += ['community_menu']
        return update_fields

    def _update_website_menus(self, menus_update_by_field=None):
        super(EventEvent, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if not menus_update_by_field or event in menus_update_by_field.get('community_menu'):
                event._update_website_menu_entry('community_menu', 'community_menu_ids', '_get_community_menu_entries')

    def _get_menu_type_field_matching(self):
        res = super(EventEvent, self)._get_menu_type_field_matching()
        res['community'] = 'community_menu'
        return res

    def _get_community_menu_entries(self):
        self.ensure_one()
        return [(_('Community'), '/event/%s/community' % slug(self), False, 80, 'community')]

    def _get_track_menu_entries(self):
        """ Remove agenda as this is now managed separately """
        self.ensure_one()
        return [
            (_('Talks'), '/event/%s/track' % slug(self), False, 10, 'track'),
            (_('Agenda'), '/event/%s/agenda' % slug(self), False, 70, False)
        ]

    def _get_track_proposal_menu_entries(self):
        """ See website_event_track._get_track_menu_entries() """
        self.ensure_one()
        return [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 15, 'track_proposal')]

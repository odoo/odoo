# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class Event(models.Model):
    _inherit = "event.event"

    meeting_room_ids = fields.One2many("event.meeting.room", "event_id", string="Meeting rooms")
    meeting_room_count = fields.Integer("Room count", compute="_compute_meeting_room_count")
    meeting_room_allow_creation = fields.Boolean(
        "Allow Room Creation", compute="_compute_meeting_room_allow_creation",
        readonly=False, store=True,
        help="Let Visitors Create Rooms")

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        """ At type onchange: synchronize. At website_menu update: synchronize. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.community_menu = event.event_type_id.community_menu
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.community_menu):
                event.community_menu = True
            elif not event.website_menu:
                event.community_menu = False

    @api.depends("meeting_room_ids")
    def _compute_meeting_room_count(self):
        meeting_room_count = self.env["event.meeting.room"].sudo()._read_group(
            domain=[("event_id", "in", self.ids)],
            groupby=['event_id'],
            aggregates=['__count'],
        )

        meeting_room_count = {
            event.id: count
            for event, count in meeting_room_count
        }

        for event in self:
            event.meeting_room_count = meeting_room_count.get(event.id, 0)

    @api.depends("event_type_id", "community_menu", "meeting_room_allow_creation")
    def _compute_meeting_room_allow_creation(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.meeting_room_allow_creation = event.event_type_id.meeting_room_allow_creation
            elif event.community_menu and event.community_menu != event._origin.community_menu:
                event.meeting_room_allow_creation = True
            elif not event.community_menu or not event.meeting_room_allow_creation:
                event.meeting_room_allow_creation = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_community_menu(self, val):
        self.community_menu = val

    def _get_menu_update_fields(self):
        return super()._get_menu_update_fields() + ['community_menu']

    def _update_website_menus(self, menus_update_by_field=None):
        super()._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('community_menu')):
                event._update_website_menu_entry('community_menu', 'community_menu_ids', 'community')

    def _get_menu_type_field_matching(self):
        res = super()._get_menu_type_field_matching()
        res['community'] = 'community_menu'
        return res

    def _get_website_menu_entries(self):
        self.ensure_one()
        return super()._get_website_menu_entries() + [
            (_('Community'), '/event/%s/community' % slug(self), 'website_event_meet.event_meet', 80, 'community')
        ]

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
            fields=["id:count"],
            groupby=["event_id"],
        )

        meeting_room_count = {
            result["event_id"][0]: result["event_id_count"]
            for result in meeting_room_count
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

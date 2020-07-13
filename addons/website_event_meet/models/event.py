# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class Event(models.Model):
    _inherit = "event.event"

    meeting_room_ids = fields.One2many("event.meeting.room", "event_id", string="Meeting rooms")
    meeting_room_count = fields.Integer("Room count", compute="_compute_meeting_room_count")
    website_meeting_room = fields.Boolean(
        "Website Community",
        help="Display community tab on website",
        compute="_compute_website_meeting_room",
        readonly=False,
        store=True,
    )
    meeting_room_menu_ids = fields.One2many(
        "website.event.menu",
        "event_id",
        string="Event Community Menus",
        domain=[("menu_type", "=", "meeting_room")],
    )

    @api.depends("event_type_id", "website_meeting_room")
    def _compute_website_meeting_room(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_meeting_room = event.event_type_id.website_meeting_room
            elif not event.website_meeting_room:
                event.website_meeting_room = False

    @api.depends("meeting_room_ids")
    def _compute_meeting_room_count(self):
        meeting_room_count = self.env["event.meeting.room"].sudo().read_group(
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

    def _update_website_menus(self, split_to_update=None):
        super(Event, self)._update_website_menus(split_to_update=split_to_update)

        for event in self:
            if event.website_meeting_room and not event.meeting_room_menu_ids:
                # add the community menu
                menu = super(Event, event)._create_menu(
                    sequence=1,
                    name=_("Community"),
                    url="/event/%s/meeting_rooms" % slug(self),
                    xml_id=False,
                )
                event.env["website.event.menu"].create(
                    {
                        "menu_id": menu.id,
                        "event_id": event.id,
                        "menu_type": "meeting_room",
                    }
                )
            elif not event.website_meeting_room:
                # remove the community menu
                event.meeting_room_menu_ids.mapped("menu_id").unlink()

    def write(self, vals):
        community_event = self.filtered(lambda e: e.website_meeting_room)
        no_community_event = self.filtered(lambda e: not e.website_meeting_room)

        super(Event, self).write(vals)

        update_events = community_event.filtered(lambda e: not e.website_meeting_room)
        update_events |= no_community_event.filtered(lambda e: e.website_meeting_room)
        update_events._update_website_menus()

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_join

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug


class EventMeetingRoom(models.Model):
    _name = "event.meeting.room"
    _description = "Event Meeting Room"
    _order = "is_pinned DESC, id"
    _inherit = {"chat.room.mixin"}

    name = fields.Char("Topic", required=True, size=50)
    event_id = fields.Many2one("event.event", "Event", required=True)
    is_pinned = fields.Boolean("Is pinned")
    summary = fields.Char("Summary", size=200)
    target_audience = fields.Char("Audience", required=True, size=30)

    def action_join(self):
        """Join the meeting room on the frontend side."""
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        url = url_join(web_base_url, f"/event/{slug(self.event_id)}/meeting_rooms?open_room_id={self.id}")
        return {
            "type": "ir.actions.act_url",
            "url": url,
        }

    @api.model
    def create(self, vals):
        vals["room_active"] = True
        vals["chat_room_id"] = vals.get(
            "chat_room_id",
            self.env["chat.room"].create({}).id,
        )
        return super(EventMeetingRoom, self).create(vals)

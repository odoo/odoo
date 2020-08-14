# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug


class EventMeetingRoom(models.Model):
    _name = "event.meeting.room"
    _description = "Event Meeting Room"
    _order = "is_pinned DESC, id"
    _inherit = [
        'chat.room.mixin',
        'website.published.mixin',
    ]

    name = fields.Char("Topic", required=True, translate=True)
    active = fields.Boolean('Active', default=True)
    is_published = fields.Boolean(copy=True)  # make the inherited field copyable
    event_id = fields.Many2one("event.event", string="Event", required=True, ondelete="cascade")
    is_pinned = fields.Boolean("Is Pinned")
    chat_room_id = fields.Many2one("chat.room", required=True, ondelete="restrict")
    summary = fields.Char("Summary", translate=True)
    target_audience = fields.Char("Audience", translate=True)

    @api.depends('name', 'event_id.name')
    def _compute_website_url(self):
        super(EventMeetingRoom, self)._compute_website_url()
        for meeting_room in self:
            if meeting_room.id:
                base_url = meeting_room.event_id.get_base_url()
                meeting_room.website_url = '%s/event/%s/meeting_room/%s' % (base_url, slug(meeting_room.event_id), slug(meeting_room))

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if not values.get("chat_room_id") and not values.get('room_name'):
                values['room_name'] = 'odoo-room-%s' % (values['name'])
        return super(EventMeetingRoom, self).create(values_list)

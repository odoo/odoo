# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.tools import remove_accents

class ChatRoomMixin(models.AbstractModel):
    """Add the chat room configuration (`chat.room`) on the needed models.

    The chat room configuration contains all information about the room. So, we store
    all the chat room logic at the same place, for all models.
    Embed chat room related fields prefixed with `room_`.
    """
    _name = "chat.room.mixin"
    _description = "Chat Room Mixin"
    ROOM_CONFIG_FIELDS = [
        ('room_name', 'name'),
        ('room_lang_id', 'lang_id'),
        ('room_max_capacity', 'max_capacity'),
        ('room_participant_count', 'participant_count')
    ]

    chat_room_id = fields.Many2one("chat.room", "Chat Room", readonly=True, copy=False, ondelete="set null")
    # chat room related fields
    room_name = fields.Char("Room Name", related="chat_room_id.name")
    room_is_full = fields.Boolean("Room Is Full", related="chat_room_id.is_full")
    room_lang_id = fields.Many2one("res.lang", "Language", related="chat_room_id.lang_id", readonly=False)
    room_max_capacity = fields.Selection(string="Max capacity", related="chat_room_id.max_capacity", readonly=False, required=True)
    room_participant_count = fields.Integer("Participant count", related="chat_room_id.participant_count", readonly=False)
    room_last_activity = fields.Datetime("Last activity", related="chat_room_id.last_activity")
    room_max_participant_reached = fields.Integer("Peak participants", related="chat_room_id.max_participant_reached")

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if any(values.get(fmatch[0]) for fmatch in self.ROOM_CONFIG_FIELDS) and not values.get('chat_room_id'):
                if values.get('room_name'):
                    values['room_name'] = self._jitsi_sanitize_name(values['room_name'])
                room_values = dict((fmatch[1], values[fmatch[0]]) for fmatch in self.ROOM_CONFIG_FIELDS if values.get(fmatch[0]))
                values['chat_room_id'] = self.env['chat.room'].create(room_values).id
        return super(ChatRoomMixin, self).create(values_list)

    def write(self, values):
        if any(values.get(fmatch[0]) for fmatch in self.ROOM_CONFIG_FIELDS):
            if values.get('room_name'):
                values['room_name'] = self._jitsi_sanitize_name(values['room_name'])
            for document in self.filtered(lambda doc: not doc.chat_room_id):
                room_values = dict((fmatch[1], values[fmatch[0]]) for fmatch in self.ROOM_CONFIG_FIELDS if values.get(fmatch[0]))
                document.chat_room_id = self.env['chat.room'].create(room_values).id
        return super(ChatRoomMixin, self).write(values)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for room, vals in zip(self, vals_list):
            if not room.chat_room_id:
                continue
            chat_room_default = {}
            if 'room_name' not in default:
                chat_room_default['name'] = self._jitsi_sanitize_name(room.chat_room_id.name)
            vals['chat_room_id'] = room.chat_room_id.copy(default=chat_room_default).id
        return vals_list

    def unlink(self):
        rooms = self.chat_room_id
        res = super(ChatRoomMixin, self).unlink()
        rooms.unlink()
        return res

    def _jitsi_sanitize_name(self, name):
        sanitized = re.sub(r'[^\w+.]+', '-', remove_accents(name).lower())
        counter, sanitized_suffixed = 1, sanitized
        existing = self.env['chat.room'].search([('name', '=like', '%s%%' % sanitized)]).mapped('name')
        while sanitized_suffixed in existing:
            sanitized_suffixed = '%s-%d' % (sanitized, counter)
            counter += 1
        return sanitized_suffixed

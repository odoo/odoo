# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from uuid import uuid4

from odoo import api, fields, models
from odoo.tools import remove_accents


class ChatRoom(models.Model):
    """ Store all useful information to manage chat room (currently limited
    to Jitsi). This model embeds all information about the chat room. We do not
    store them in the related mixin (see chat.room.mixin) to avoid to add too
    many fields on the models which want to use the chat room mixin as the
    behavior can be optional in those models.

    The participant count is automatically updated thanks to the chat room widget
    to avoid having a costly computed field with a members model.
    """
    _name = "chat.room"
    _description = "Chat Room"

    def _default_name(self):
        return "odoo-room-%s" % str(uuid4())[:8]

    name = fields.Char(
        "Room Name", required=True, copy=False,
        default=lambda self: self._default_name())
    is_full = fields.Boolean("Full", compute="_compute_is_full")
    lang_id = fields.Many2one(
        "res.lang", "Language",
        default=lambda self: self.env["res.lang"].search([("code", "=", self.env.user.lang)], limit=1))
    max_capacity = fields.Selection(
        [("4", "4"), ("8", "8"), ("12", "12"), ("16", "16"),
         ("20", "20"), ("no_limit", "No limit")], string="Max capacity",
        default="8", required=True)
    participant_count = fields.Integer("Participant count", default=0, copy=False)
    # reporting fields
    last_activity = fields.Datetime(
        "Last Activity", copy=False, readonly=True,
        default=lambda self: fields.Datetime.now())
    max_participant_reached = fields.Integer(
        "Max participant reached", copy=False, readonly=True,
        help="Maximum number of participant reached in the room at the same time")

    @api.depends("max_capacity", "participant_count")
    def _compute_is_full(self):
        for room in self:
            if room.max_capacity == "no_limit":
                room.is_full = False
            else:
                room.is_full = room.participant_count >= int(room.max_capacity)

    def _jitsi_sanitize_name(self, name):
        return re.sub(r'[^\w+.]+', '-', remove_accents(name).lower())

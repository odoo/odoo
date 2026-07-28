# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    meeting_room_allow_creation = fields.Boolean(
        "Allow Room Creation", compute='_compute_meeting_room_allow_creation',
        readonly=False, store=True,
        help="Let Visitors Create Rooms")

    @api.depends('community_menu')
    def _compute_meeting_room_allow_creation(self):
        for event_type in self:
            event_type.meeting_room_allow_creation = event_type.community_menu

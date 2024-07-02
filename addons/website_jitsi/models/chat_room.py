# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ChatRoom(models.Model):
    _inherit = "chat.room"

    jitsi_server_domain = fields.Char(
        'Jitsi Server Domain', compute='_compute_jitsi_server_domain',
        help='The Jitsi server domain can be customized through the settings to use a different server than the default "meet.jit.si"')

    participant_count = fields.Integer("Participant count", default=0, copy=False)

    def _compute_jitsi_server_domain(self):
        jitsi_server_domain = self.env['ir.config_parameter'].sudo().get_param(
            'website_jitsi.jitsi_server_domain', 'meet.jit.si')

        for room in self:
            room.jitsi_server_domain = jitsi_server_domain

    def get_room_url(self):
        self.ensure_one()
        return self.jitsi_server_domain

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ChatRoom(models.Model):
    _inherit = "chat.room"

    chat_room_provider = fields.Selection(selection_add=[('jitsi', 'Jitsi')], default='jitsi', ondelete={'jitsi': 'set discuss'})
    jitsi_server_domain = fields.Char(
        'Jitsi Server Domain', compute='_compute_jitsi_server_domain',
        help='The Jitsi server domain can be customized through the settings to use a different server than the default "meet.jit.si"')

    # The participant count is automatically updated thanks to the chat room widget
    # to avoid having a costly computed field with a members model.
    participant_count = fields.Integer("Participant count", store=True, default=0, copy=False)

    def _compute_jitsi_server_domain(self):
        jitsi_server_domain = self.env['ir.config_parameter'].sudo().get_param(
            'website_event_jitsi.jitsi_server_domain', 'meet.jit.si')

        for room in self:
            room.jitsi_server_domain = jitsi_server_domain

    # Override the compute method from the discuss module to avoid any missuse
    @api.depends("discuss_channel_id.rtc_session_ids")
    def _compute_participant_count(self):
        for room in self:
            if room.chat_room_provider == 'discuss':
                room.participant_count = len(room.discuss_channel_id.rtc_session_ids)

    def get_room_url(self):
        self.ensure_one()
        if self.chat_room_provider == 'discuss':
            return super().get_room_url()
        return self.jitsi_server_domain

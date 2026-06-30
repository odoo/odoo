# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class DiscussChannelRtcSession(models.Model):
    _inherit = "discuss.channel.rtc.session"

    @api.model_create_multi
    def create(self, vals_list):
        rtc_sessions = super().create(vals_list)
        for livechat_session in rtc_sessions.filtered(
            lambda s: s.channel_member_id.livechat_member_type in ("agent", "visitor")
        ):
            call_history = livechat_session.channel_id.call_history_ids.sorted(
                lambda c: (c.create_date, c.id)
            )[-1]
            call_history.livechat_participant_history_ids |= (
                livechat_session.channel_member_id.livechat_member_history_ids
            )
        return rtc_sessions

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models


class ChannelMember(models.Model):
    _inherit = 'mail.channel.member'

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin read livechat sessions with no activity for at least one day to
            clean the operator's interface """
        members = self.env['mail.channel.member'].search([
            ('is_pinned', '=', True),
            ('last_seen_dt', '<=', datetime.now() - timedelta(days=1)),
            ('channel_id.channel_type', '=', 'livechat'),
        ])
        sessions_to_be_unpinned = members.filtered(lambda m: m.message_unread_counter == 0)
        sessions_to_be_unpinned.write({'is_pinned': False})
        self.env['bus.bus']._sendmany([(member.partner_id, 'mail.channel/unpin', {'id': member.channel_id.id}) for member in sessions_to_be_unpinned])

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

    def _get_partner_data(self, fields=None):
        if self.channel_id.channel_type == 'livechat':
            data = {
                'active': self.partner_id.active,
                'id': self.partner_id.id,
                'is_public': self.partner_id.is_public,
            }
            if self.partner_id.user_livechat_username:
                data['user_livechat_username'] = self.partner_id.user_livechat_username
            else:
                data['name'] = self.partner_id.name
            if not self.partner_id.is_public:
                data['country'] = {
                    'code': self.partner_id.country_id.code,
                    'id': self.partner_id.country_id.id,
                    'name': self.partner_id.country_id.name,
                } if self.partner_id.country_id else [('clear',)]
            return data
        return super()._get_partner_data(fields=fields)

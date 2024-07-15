# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models, fields
from odoo.addons.mail.tools.discuss import Store


class ChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin read livechat sessions with no activity for at least one day to
            clean the operator's interface """
        members = self.env['discuss.channel.member'].search([
            ('is_pinned', '=', True),
            ('last_seen_dt', '<=', datetime.now() - timedelta(days=1)),
            ('channel_id.channel_type', '=', 'livechat'),
        ])
        sessions_to_be_unpinned = members.filtered(lambda m: m.message_unread_counter == 0)
        sessions_to_be_unpinned.write({'unpin_dt': fields.Datetime.now()})
        self.env['bus.bus']._sendmany([(member.partner_id, 'discuss.channel/unpin', {'id': member.channel_id.id}) for member in sessions_to_be_unpinned])

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        for member in self.filtered(lambda m: m.channel_id.channel_type == "livechat"):
            # sudo: mail.channel - reading livechat channel to check whether current member is a bot is allowed
            store.add(
                "discuss.channel.member",
                {
                    "id": member.id,
                    "is_bot": member.partner_id
                    in member.channel_id.sudo().livechat_channel_id.rule_ids.chatbot_script_id.operator_partner_id,
                },
            )

    def _partner_data_to_store(self, store: Store, fields=None):
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
                } if self.partner_id.country_id else False
            store.add("res.partner", data)
        else:
            super()._partner_data_to_store(store, fields=fields)

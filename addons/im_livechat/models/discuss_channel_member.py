# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models, fields
from odoo.osv import expression
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
        for member in sessions_to_be_unpinned:
            member._bus_send("discuss.channel/unpin", {"id": member.channel_id.id})

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        for member in self.filtered(lambda m: m.channel_id.channel_type == "livechat"):
            # sudo: discuss.channel - reading livechat channel to check whether current member is a bot is allowed
            store.add(
                member,
                {
                    "is_bot": member.partner_id
                    in member.channel_id.sudo().livechat_channel_id.rule_ids.chatbot_script_id.operator_partner_id,
                },
            )

    def _get_store_partner_fields(self, fields):
        self.ensure_one()
        if self.channel_id.channel_type == 'livechat':
            return ["active", "avatar_128", "country", "is_public", "user_livechat_username"]
        return super()._get_store_partner_fields(fields)

    def _get_rtc_invite_members_domain(self, *a, **kw):
        domain = super()._get_rtc_invite_members_domain(*a, **kw)
        chatbot = self.channel_id.chatbot_current_step_id.chatbot_script_id
        if self.channel_id.channel_type == "livechat" and chatbot:
            domain = expression.AND(
                [
                    domain,
                    [("partner_id", "!=", chatbot.operator_partner_id.id)],
                ]
            )
        return domain

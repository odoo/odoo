# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models


class DiscussChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    @api.autovacuum
    def _gc_unpin_whatsapp_channels(self):
        """ Unpin read whatsapp channels with no activity for at least one day to
            clean the operator's interface """
        members = self.env['discuss.channel.member'].search([
            ('is_pinned', '=', True),
            ('last_seen_dt', '<=', datetime.now() - timedelta(days=1)),
            ('channel_id.channel_type', '=', 'whatsapp'),
        ])
        members_to_be_unpinned = members.filtered(lambda m: m.message_unread_counter == 0)
        members_to_be_unpinned.write({'is_pinned': False})
        self.env['bus.bus']._sendmany([
            (member.partner_id, 'discuss.channel/unpin', {'id': member.channel_id.id})
            for member in members_to_be_unpinned
        ])

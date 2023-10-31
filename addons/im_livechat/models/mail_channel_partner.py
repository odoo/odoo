# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChannelPartner(models.Model):
    _inherit = 'mail.channel.partner'

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin livechat sessions with no activity for at least one day to
            clean the operator's interface """
        self.env.cr.execute("""
            UPDATE mail_channel_partner
            SET is_pinned = false
            WHERE id in (
                SELECT cp.id FROM mail_channel_partner cp
                INNER JOIN mail_channel c on c.id = cp.channel_id
                WHERE c.channel_type = 'livechat' AND cp.is_pinned is true AND
                    cp.write_date < current_timestamp - interval '1 day'
            )
        """)

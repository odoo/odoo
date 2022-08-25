# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChannelMember(models.Model):
    _inherit = 'mail.channel.member'

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin livechat sessions with no activity for at least one day to
            clean the operator's interface """
        self.env.cr.execute("""
            UPDATE mail_channel_member
            SET is_pinned = false
            WHERE id in (
                SELECT cm.id FROM mail_channel_member cm
                INNER JOIN mail_channel c on c.id = cm.channel_id
                WHERE c.channel_type = 'livechat' AND cm.is_pinned is true AND
                    cm.write_date < current_timestamp - interval '1 day'
            )
        """)

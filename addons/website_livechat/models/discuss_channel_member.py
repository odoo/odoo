# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    def _write_after_hook(self, vals):
        """Override to clean an empty live chat conversation. This is typically called when the
        agent sends a chat request to a website.visitor but does not speak to them and hides the
        conversation."""
        super()._write_after_hook(vals)
        if any(field in vals for field in ["last_interest_dt", "unpin_dt"]):
            # sudo: discuss.channel - empty live chat request can be unlinked
            self.filtered(
                lambda member: not member.is_pinned
                and member.channel_id.is_pending_chat_request
                and not member.channel_id.message_count,
            ).channel_id.sudo().unlink()

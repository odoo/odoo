# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _get_access_action(self, access_uid=None, force_website=False):
        """Point portal users to the conversation embedded in the portal."""
        self.ensure_one()
        if self.env.user._is_portal():
            return {
                "type": "ir.actions.act_url",
                "url": f"/my/conversations/{self.id}",
                "target": "self",
                "target_type": "public",
            }
        return super()._get_access_action(access_uid=access_uid, force_website=force_website)

    def _get_invite_urls_by_emails(self, emails):
        urls = super()._get_invite_urls_by_emails(emails)
        portal_emails = self.env["res.users"].search_fetch([
                ("partner_id.email_normalized", "in", list(emails)),
                ("share", "=", True),
                ("active", "=", True),
            ], ["email_normalized"]).mapped("email_normalized")
        for email in portal_emails:
            urls[email] = f"/my/conversations/{self.id}"
        return urls

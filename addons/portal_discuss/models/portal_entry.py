# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalEntryDiscuss(models.Model):
    _inherit = "portal.entry"

    def should_show_portal_card(self):
        res = super().should_show_portal_card()
        external_id = self.get_external_id().get(self.id, "")
        if external_id == "portal_discuss.portal_entry_discuss":
            return bool(
                self.env["discuss.channel.member"].search_count(
                    [("partner_id", "=", self.env.user.partner_id.id)],
                    limit=1,
                ),
            )
        return res

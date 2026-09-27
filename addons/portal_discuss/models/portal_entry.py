# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalEntryDiscuss(models.Model):
    _inherit = "portal.entry"

    def _filter_visible_portal_cards(self):
        visible_entries = super()._filter_visible_portal_cards()
        discuss_entry = self.env.ref("portal_discuss.portal_entry_discuss", raise_if_not_found=False)
        if discuss_entry and discuss_entry in self:
            is_visible = bool(
                self.env["discuss.channel.member"].search_count(
                    [("partner_id", "=", self.env.user.partner_id.id)],
                    limit=1,
                ),
            )
            if is_visible:
                visible_entries |= discuss_entry
            else:
                visible_entries -= discuss_entry
        return visible_entries

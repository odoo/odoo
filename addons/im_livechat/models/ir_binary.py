# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        """Custom access check allowing to retrieve an operator's avatar.

        Here, we assume that if you are a member of at least one
        im_livechat.channel, then it's ok to make your avatar publicly
        available.

        We also make the chatbot operator avatars publicly available."""
        if record._name == "res.partner" and field == "avatar_128":
            domain = [("user_ids.partner_id", "in", record.ids)]
            if self.env["im_livechat.channel"].sudo().search_count(domain, limit=1):
                return record.sudo()
            domain = [("operator_partner_id", "in", record.ids)]
            if self.env["chatbot.script"].sudo().search_count(domain, limit=1):
                return record.sudo()
        return super()._find_record_check_access(record, access_token, field)

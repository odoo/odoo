# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if record._name in ["res.partner", "mail.guest"] and field == "avatar_128":
            current_partner, current_guest = self.env["res.partner"]._get_current_persona()
            if current_partner or current_guest:
                domain = []
                if record._name == "res.partner":
                    domain.append(("channel_member_ids", "any", [("partner_id", "=", record.id)]))
                else:
                    domain.append(("channel_member_ids", "any", [("guest_id", "=", record.id)]))
                if current_partner:
                    domain.append(("channel_member_ids", "any", [("partner_id", "=", current_partner.id)]))
                else:
                    domain.append(("channel_member_ids", "any", [("guest_id", "=", current_guest.id)]))
                # sudo: discuss.channel - checking existence of common channel to display avatar
                if self.env["discuss.channel"].sudo().search_count(domain, limit=1):
                    return record.sudo()
        return super()._find_record_check_access(record, access_token, field)

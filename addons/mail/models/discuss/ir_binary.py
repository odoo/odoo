# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if record._name in ["res.partner", "mail.guest"] and field == "avatar_128":
            persona = self.env["discuss.persona"]._get_current_persona()
            if persona:
                domain = []
                if record._name == "res.partner":
                    domain.append(("channel_member_ids", "any", [("partner_id", "=", record.id)]))
                else:
                    domain.append(("channel_member_ids", "any", [("guest_id", "=", record.id)]))
                if persona.partner_id:
                    domain.append(("channel_member_ids", "any", [("partner_id", "=", persona.partner_id.id)]))
                else:
                    domain.append(("channel_member_ids", "any", [("guest_id", "=", persona.guest_id.id)]))
                if self.env["discuss.channel"].search_count(domain, limit=1):
                    return record.sudo()
        return super()._find_record_check_access(record, access_token, field)

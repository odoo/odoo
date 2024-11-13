# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if record._name in ["res.partner", "mail.guest"] and field == "avatar_128":
            current_partner, current_guest = self.env["res.partner"]._get_current_persona()
            if current_partner or current_guest:
                member_lookup_domains = []
                if record._name == "res.partner":
                    member_lookup_domains.append([("partner_id", "=", record.id)])
                else:
                    member_lookup_domains.append([("guest_id", "=", record.id)])
                if current_partner:
                    member_lookup_domains.append([("partner_id", "=", current_partner.id)])
                else:
                    member_lookup_domains.append([("guest_id", "=", current_guest.id)])
                domain = [('channel_member_ids', 'any', OR(member_lookup_domains))]
                if self.env["discuss.channel"].search_count(domain, limit=1):
                    return record.sudo()
        return super()._find_record_check_access(record, access_token, field)

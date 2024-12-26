# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import AccessError, MissingError


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if not (record._name in ["res.partner", "mail.guest"] and field == "avatar_128"):
            return super()._find_record_check_access(record, access_token, field)

        # implement fallback permission checks for avatar visibility, based on channel membership, but
        # *always* try calling super() first, because the fallback checks are not cheap! In many cases
        # the user has direct access to the avatar, without requiring specific channel membership.
        #
        # TODO: in master this complexity could be avoided by using a specific route for accessing
        #  channel avatars, based on the channel ID. This way we won't need to search all channels
        #  for a possible membership, when no direct access is granted.
        try:
            return super()._find_record_check_access(record, access_token, field)
        except (AccessError, MissingError) as e:
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
                if self.env["discuss.channel"].search_count(domain, limit=1):
                    return record.sudo()
            raise e

from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _convert_visitor_to_lead(self, partner, key):
        lead = super()._convert_visitor_to_lead(partner, key)
        visitor_sudo = self.livechat_visitor_id.sudo()
        if visitor_sudo:
            _debug.lifecycle(
                "livechat_lead_linked_to_visitor",
                lead=lead,
                visitor=visitor_sudo,
                country_from_visitor=not lead.country_id,
            )
            visitor_sudo.write({"lead_ids": [(4, lead.id)]})
            lead.country_id = lead.country_id or visitor_sudo.country_id
        return lead

import logging

from odoo import api, models
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        # Visitor analytics are internal merge metadata, scoped to these contacts.
        visitors = dst_partner.sudo().visitor_ids | src_partners.sudo().visitor_ids
        dst_visitor = visitors[:1]
        _debug.lifecycle(
            "partner_merge_visitors",
            destination=dst_partner.id,
            sources=len(src_partners),
            visitors=len(visitors),
        )
        for visitor in visitors[1:]:
            visitor._merge_visitor(dst_visitor)

        super()._update_foreign_keys(src_partners, dst_partner)

        if dst_visitor:
            dst_visitor.access_token = str(dst_partner.id)
            _logger.debug(
                "Partner merge destination=%s visitor=%s merged_visitors=%s",
                dst_partner.id,
                dst_visitor.id,
                len(visitors),
            )

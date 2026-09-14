import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        visitors = dst_partner.visitor_ids | src_partners.visitor_ids
        dst_visitor = visitors[:1]
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

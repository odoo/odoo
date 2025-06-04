from odoo import models
from odoo.http import request


class PortalOpportunityCard(models.Model):
    _inherit = 'portal.entry'

    def should_show_portal_card(self):
        res = super().should_show_portal_card()
        external_id = self.get_external_id().get(self.id, '')
        if external_id == 'website_crm_partner_assign.portal_entry_opportunities':
            return bool(request.env.user.partner_id.grade_id or request.env.user.commercial_partner_id.grade_id)
        return res

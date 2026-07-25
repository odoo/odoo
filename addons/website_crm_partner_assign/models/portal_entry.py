from odoo import models


class PortalOpportunityCard(models.Model):
    _inherit = 'portal.entry'

    def _filter_visible_portal_cards(self):
        visible_entries = super()._filter_visible_portal_cards()
        opportunity_entry = self.env.ref('website_crm_partner_assign.portal_entry_opportunities', raise_if_not_found=False)
        if opportunity_entry and opportunity_entry in self:
            if self.env.user.partner_id.grade_id or self.env.user.commercial_partner_id.grade_id:
                visible_entries |= opportunity_entry
            else:
                visible_entries -= opportunity_entry
        return visible_entries

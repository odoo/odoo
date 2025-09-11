# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_contact_opportunities_domain(self):
        all_partners = self._fetch_children_partners_for_hierarchy().ids
        return ['|', ('partner_assigned_id', 'in', all_partners), ('partner_id', 'in', all_partners)]

    def _compute_opportunity_count(self):
        if not self.ids or not self.env.user.has_group('sales_team.group_sale_salesman'):
            return super()._compute_opportunity_count()

        self.opportunity_count = 0
        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            self._get_contact_opportunities_domain(),
            ['partner_assigned_id', 'partner_id'], ['__count']
        )
        current_pids = set(self._ids)
        for assign_partner, partner, count in opportunity_data:
            # this variable is used to keep the track of the partner
            seen_partners = set()
            while partner or assign_partner:
                if assign_partner and assign_partner.id in current_pids and assign_partner not in seen_partners:
                    assign_partner.opportunity_count += count
                    seen_partners.add(assign_partner)
                if partner and partner.id in current_pids and partner not in seen_partners:
                    partner.opportunity_count += count
                    seen_partners.add(partner)
                assign_partner = assign_partner.parent_id
                partner = partner.parent_id

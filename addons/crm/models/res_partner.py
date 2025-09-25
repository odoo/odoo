# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    opportunity_count = fields.Integer(
        string="Opportunity Count",
        groups='sales_team.group_sale_salesman',
        compute='_compute_opportunity_count',
    )

    def _compute_opportunity_count(self):
        self.opportunity_count = 0
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)], ['parent_id'],
        )

        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        for partner, count in opportunity_data:
            while partner:
                if partner.id in self_ids:
                    partner.opportunity_count += count
                partner = partner.parent_id

    def action_view_opportunity(self):
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['context'] = {}
        action['context'] = {
            'search_default_filter_won_status_won': 1,
            'search_default_filter_won_status_lost': 1,
            'search_default_filter_won_status_pending': 1,
            'active_test': False,
        }
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id', '=', self.id)]
        else:
            action['domain'] = [('partner_id', '=', self.id)]
        action['domain'] = expression.AND([action['domain'], [('active', 'in', [True, False])]])
        return action

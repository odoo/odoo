# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    opportunity_count = fields.Integer(
        string="Opportunity Count",
        groups='sales_team.group_sale_salesman',
        compute='_compute_opportunity_count',
    )

    def _fetch_children_partners_for_hierarchy(self):
        # retrieve all children partners and prefetch 'parent_id' on them, saving
        # queries for recursive parent_id browse
        return self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)], ['parent_id'],
        )

    def _get_contact_opportunities_domain(self):
        return [('partner_id', 'in', self._fetch_children_partners_for_hierarchy().ids)]

    def _compute_opportunity_count(self):
        self.opportunity_count = 0
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            return
        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            domain=self._get_contact_opportunities_domain(),
            groupby=['partner_id'], aggregates=['__count']
        )
        current_pids = set(self._ids)
        for partner, count in opportunity_data:
            while partner:
                if partner.id in current_pids:
                    partner.opportunity_count += count
                partner = partner.parent_id

    def _compute_application_statistics_hook(self):
        data_list = super()._compute_application_statistics_hook()
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            return data_list
        for partner in self.filtered('opportunity_count'):
            data_list[partner.id].append(
                {'iconClass': 'fa-star', 'value': partner.opportunity_count, 'label': _('Opportunities'), 'tagClass': 'o_tag_color_8'}
            )
        return data_list

    def action_view_opportunity(self):
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['context'] = {
            'search_default_filter_won': 1,
            'search_default_filter_ongoing': 1,
            'search_default_filter_lost': 1,
            'active_test': False,
        }
        # we want the list view first
        action['views'] = sorted(action['views'], key=lambda view: view[1] != 'list')
        action['domain'] = self._get_contact_opportunities_domain()
        return action

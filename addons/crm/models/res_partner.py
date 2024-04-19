# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    opportunity_count = fields.Integer(
        string="Opportunity Count",
        groups='sales_team.group_sale_salesman',
        compute='_compute_opportunity_count',
    )

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model == 'crm.lead' and len(self.env.context.get('active_ids', [])) <= 1:
            lead = self.env[active_model].browse(self.env.context.get('active_id')).exists()
            if lead:
                rec.update(
                    phone=lead.phone,
                    function=lead.function,
                    website=lead.website,
                    street=lead.street,
                    street2=lead.street2,
                    city=lead.city,
                    state_id=lead.state_id.id,
                    country_id=lead.country_id.id,
                    zip=lead.zip,
                )
        return rec

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

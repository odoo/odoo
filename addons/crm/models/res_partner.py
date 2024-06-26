# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression



class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    opportunity_count = fields.Integer("Opportunity", compute='_compute_opportunity_count')

    @api.model
    def default_get(self, fields):
        rec = super(Partner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model == 'crm.lead' and len(self.env.context.get('active_ids', [])) <= 1:
            lead = self.env[active_model].browse(self.env.context.get('active_id')).exists()
            if lead:
                rec.update(
                    phone=lead.phone,
                    mobile=lead.mobile,
                    function=lead.function,
                    title=lead.title.id,
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
        # retrieve all children partners and prefetch 'parent_id' on them
        return self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)], ['parent_id'],
        )

    def _get_contact_opportunities_domain(self):
        return [('partner_id', 'in', self._fetch_children_partners_for_hierarchy().ids)]

    def _compute_opportunity_count(self):
        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            domain=self._get_contact_opportunities_domain(),
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.opportunity_count = 0
        for partner, count in opportunity_data:
            while partner:
                if partner.id in self_ids:
                    partner.opportunity_count += count
                partner = partner.parent_id

    def action_view_opportunity(self):
        '''
        This function returns an action that displays the opportunities from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['context'] = {}
        action['domain'] = expression.AND([self._get_contact_opportunities_domain(), [('active', 'in', [True, False])]])
        return action

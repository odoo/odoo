# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, SUPERUSER_ID

class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    crm_lead_activated = fields.Boolean('Use Leads', compute='_compute_crm_lead_activated')
    lead_count = fields.Integer('Lead Count', groups='sales_team.group_sale_salesman', compute="_compute_global_opportunity_and_lead_count")
    opportunity_count = fields.Integer('Opportunity Count', groups='sales_team.group_sale_salesman', compute="_compute_global_opportunity_and_lead_count")

    def _compute_crm_lead_activated(self):
        for campaign in self:
            campaign.crm_lead_activated = self.env.user.has_group('crm.group_use_lead')

    def _compute_global_opportunity_and_lead_count(self):
        lead_data = self.env['crm.lead'].with_context(active_test=False).read_group([
            ('campaign_id', 'in', self.ids)],
            ['campaign_id'], ['campaign_id'])
        data_map = {datum['campaign_id'][0]: datum['campaign_id_count'] for datum in lead_data}
        if self.env.user.has_group('crm.group_use_lead'):
            for campaign in self:
                campaign.lead_count = data_map.get(campaign.id, 0)
                campaign.opportunity_count = 0
        else:
            for campaign in self:
                campaign.lead_count = 0
                campaign.opportunity_count = data_map.get(campaign.id, 0)

    def action_redirect_to_leads(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('campaign_id', '=', self.id)]
        action['context'] = {'default_type': 'lead', 'active_test': False}
        return action

    def action_redirect_to_opportunities(self):
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['view_mode'] = 'tree,kanban,graph,pivot,form,calendar'
        action['domain'] = [('campaign_id', '=', self.id)]
        action['context'] = {'active_test': False}
        return action

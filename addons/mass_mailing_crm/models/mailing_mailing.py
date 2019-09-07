# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.osv import expression


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    crm_lead_activated = fields.Boolean('Use Leads', compute='_compute_crm_lead_activated')
    crm_lead_count = fields.Integer('Lead Count', groups='sales_team.group_sale_salesman', compute='_compute_crm_lead_and_opportunities_count')
    crm_opportunities_count = fields.Integer('Opportunities Count', groups='sales_team.group_sale_salesman', compute='_compute_crm_lead_and_opportunities_count')

    def _compute_crm_lead_activated(self):
        for mass_mailing in self:
            mass_mailing.crm_lead_activated = self.env.user.has_group('crm.group_use_lead')

    @api.depends('crm_lead_activated')
    def _compute_crm_lead_and_opportunities_count(self):
        for mass_mailing in self:
            lead_and_opportunities_count = mass_mailing.crm_lead_count = self.env['crm.lead'] \
                    .with_context(active_test=False) \
                    .search_count(self._get_crm_utm_domain())
            if mass_mailing.crm_lead_activated:
                mass_mailing.crm_lead_count = lead_and_opportunities_count
                mass_mailing.crm_opportunities_count = 0
            else:
                mass_mailing.crm_lead_count = 0
                mass_mailing.crm_opportunities_count = lead_and_opportunities_count

    def action_redirect_to_leads(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = self._get_crm_utm_domain()
        action['context'] = {'default_type': 'lead', 'active_test': False, 'create': False}
        return action

    def action_redirect_to_opportunities(self):
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['view_mode'] = 'tree,kanban,graph,pivot,form,calendar'
        action['domain'] = self._get_crm_utm_domain()
        action['context'] = {'active_test': False, 'create': False}
        return action

    def _get_crm_utm_domain(self):
        """ We want all records that match the UTMs """
        domain = []
        if self.campaign_id:
            domain = expression.AND([domain, [('campaign_id', '=', self.campaign_id.id)]])
        if self.source_id:
            domain = expression.AND([domain, [('source_id', '=', self.source_id.id)]])
        if self.medium_id:
            domain = expression.AND([domain, [('medium_id', '=', self.medium_id.id)]])
        if not domain:
            domain = expression.AND([domain, [(0, '=', 1)]])

        return domain

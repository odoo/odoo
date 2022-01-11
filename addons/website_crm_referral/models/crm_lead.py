# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import models, fields, api


class Lead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'referral.abstract']

    referred_email = fields.Char(related='email_from')
    referred_name = fields.Char(related='contact_name')
    referred_company_name = fields.Char(related='partner_name')

    def _get_state_for_referral(self):
        self.ensure_one()
        first_stage = self._stage_find(team_id=self.team_id.id)
        if not self.active and self.probability == 0:
            return 'cancel'
        if self.type == 'lead' or self.stage_id == first_stage:
            return 'new'
        if self.stage_id.is_won:
            return 'done'
        return 'in_progress'

    def write(self, vals):
        if self.env.user.has_group('website_crm_referral.group_lead_referral') and \
                any([elem in vals for elem in ['stage_id', 'type', 'active', 'probability']]):
            referral_campaign = self.env.ref('website_sale_referral.utm_campaign_referral')
            leads = self.filtered(lambda l: l.campaign_id == referral_campaign and not l.deserve_reward)
            old_states = {lead: lead._get_referral_statuses(lead.source_id, lead.referred_email) for lead in leads}
            r = super().write(vals)
            new_states = {lead: lead._get_referral_statuses(lead.source_id, lead.referred_email) for lead in leads}
            for lead in leads:
                lead._check_and_apply_progress(old_states[lead], new_states[lead])
            return r
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        campaign = self.env.ref('website_sale_referral.utm_campaign_referral')
        referral_leads = res.filtered(lambda lead: lead.campaign_id == campaign)
        if referral_leads:
            vals = {}
            if self.env.company.salesperson_id:
                vals['user_id'] = self.env.company.salesperson_id.id
            if self.env.company.salesteam_id:
                vals['team_id'] = self.env.company.salesteam_id.id
            tag_ids = literal_eval(self.env['ir.config_parameter'].sudo().get_param('website_sale_referral.lead_tag_ids') or '[]')
            if tag_ids:
                vals['tag_ids'] = [(4, tag_id) for tag_id in tag_ids]
            referral_leads.write(vals)
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from ast import literal_eval
from odoo.osv import expression


class Lead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'referral.abstract', 'mail.activity.mixin']

    referred_email = fields.Char(related='email_from')
    referred_name = fields.Char(related='contact_name')
    referred_company_name = fields.Char(related='partner_name')

    def _get_state_for_referral(self):
        self.ensure_one()
        first_stage = self.env['crm.stage'].search([], limit=1).id
        if not self.active and self.probability == 0:
            return 'cancel'
        elif self.type == 'lead' or self.stage_id.id == first_stage:
            return 'new'
        elif self.stage_id.is_won:
            return 'done'
        return 'in_progress'

    def write(self, vals):
        if self.env.user.has_group('website_crm_referral.group_lead_referral') and \
           any([elem in vals for elem in ['stage_id', 'type', 'active', 'probability']]):
            leads = list(filter(lambda l: l.campaign_id == self.env.ref('website_sale_referral.utm_campaign_referral') and not l.deserve_reward, self))
            old_states = {}
            for lead in leads:
                old_states[lead] = lead._get_referral_statuses(lead.source_id, lead.referred_email)
            r = super().write(vals)
            for lead in leads:
                new_state = lead._get_referral_statuses(lead.source_id, lead.referred_email)
                lead._check_referral_progress(old_states[lead], new_state)
            return r
        else:
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('campaign_id', None) == self.env.ref('website_sale_referral.utm_campaign_referral').id:
                if 'user_id' not in vals:
                    vals['user_id'] = self.env.company.salesperson_id.id
                if 'team_id' not in vals:
                    vals['team_id'] = self.env.company.salesteam_id.id

                tags = [(6, 0, literal_eval(self.env['ir.config_parameter'].sudo().get_param('website_sale_referral.lead_tag_ids') or '[]'))]
                if tags:
                    if 'tag_ids' in vals:
                        vals['tag_ids'].extend(tags)
                    else:
                        vals['tag_ids'] = tags
        return super(Lead, self).create(vals)

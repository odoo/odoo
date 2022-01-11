# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_referral_reward_on_lead = fields.Boolean(compute='_compute_group_referral_reward_on_lead', implied_group="website_crm_referral.group_lead_referral", readonly=False, store=True)
    referral_reward_on_lead = fields.Selection(
        [('sale_order', 'Reward based on paid Sales Order'), ('lead', 'Reward based on Leads won')],
        string='Rewards based on',
        required=True,
        default='sale_order',
        help=' If "reward based on paid Sales Order", the status is changed to "won" once all invoices linked to the SO are paid. If "reward based on Leads won", the status is changed to "won" once the lead reaches a stage flagged in as "won stage"')

    lead_tag_ids = fields.Many2many('crm.lead.tag', string="Lead tags")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        if self.env.user.has_group('website_crm_referral.group_lead_referral'):
            res['referral_reward_on_lead'] = 'lead'
        else:
            res['referral_reward_on_lead'] = 'sale_order'
        res['lead_tag_ids'] = [(6, 0, literal_eval(self.env['ir.config_parameter'].sudo().get_param('website_sale_referral.lead_tag_ids') or '[]'))]

        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('website_sale_referral.lead_tag_ids', self.lead_tag_ids.ids)
        return res

    @api.depends('referral_reward_on_lead')
    def _compute_group_referral_reward_on_lead(self):
        for wizard in self:
            wizard.group_referral_reward_on_lead = wizard.referral_reward_on_lead == 'lead'

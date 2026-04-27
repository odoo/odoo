# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrReferralOnboarding(models.Model):
    _name = 'hr.referral.onboarding'
    _description = 'Welcome Onboarding in Referral App'
    _order = 'sequence'
    _rec_name = 'text'

    sequence = fields.Integer()
    text = fields.Text(required=True, translate=True)
    image = fields.Binary(required=True)
    company_id = fields.Many2one('res.company', 'Company')

    def action_relaunch_onboarding(self):
        self.env['res.users'].sudo().search([
            ('company_id', 'in', self.env.companies.ids),
            ('share', '=', False),
        ]).write({'hr_referral_onboarding_page': False})

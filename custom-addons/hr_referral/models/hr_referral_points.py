# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class HrReferralPoints(models.Model):
    _name = 'hr.referral.points'
    _description = 'Points line for referrals'
    _rec_name = 'points'

    applicant_id = fields.Many2one('hr.applicant')
    applicant_subject = fields.Char(related='applicant_id.name')
    applicant_name = fields.Char(related='applicant_id.partner_name')
    hr_referral_reward_id = fields.Many2one('hr.referral.reward', string="Reward")
    ref_user_id = fields.Many2one('res.users', required=True, string='User')
    points = fields.Integer('Points')
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage')
    sequence_stage = fields.Integer('Sequence of stage', related='stage_id.sequence')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

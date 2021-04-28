# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _inherit = ['loyalty.program']

    website_reward_ids = fields.One2many('loyalty.website.reward', 'loyalty_program_id', string='eCommerce Rewards')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    responsible_id = fields.Many2one(
        'res.users',
        string='Reward manager',
        help='This person will get a new activity once a referral reaches the stage "won". Then he can take contact with the referrer to send him a reward')

    salesteam_id = fields.Many2one('crm.team', string="Salesteam")
    salesperson_id = fields.Many2one('res.users', string="Salesperson")

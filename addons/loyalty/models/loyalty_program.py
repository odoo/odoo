# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _description = 'Loyalty Program'

    name = fields.Char(string='Loyalty Program Name', index=True, required=True, translate=True, help="An internal identification for the loyalty program configuration")
    points = fields.Float(string='Point per $ spent', help="How many loyalty points are given to the customer by sold currency")
    rule_ids = fields.One2many('loyalty.rule', 'loyalty_program_id', string='Rules')
    active = fields.Boolean(default=True)

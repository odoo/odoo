# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'

    name = fields.Char(string='Loyalty Program Name', index=True, required=True, help="An internal identification for the loyalty program configuration")
    pp_currency = fields.Float(string='Points per currency', help="How many loyalty points are given to the customer by sold currency")
    pp_product = fields.Float(string='Points per product', help="How many loyalty points are given to the customer by product sold")
    pp_order = fields.Float(string='Points per order', help="How many loyalty points are given to the customer for each sale or order")
    rounding = fields.Float(string='Points Rounding', default=1, help="The loyalty point amounts are rounded to multiples of this value.")
    rule_ids = fields.One2many('loyalty.rule', 'loyalty_program_id', string='Rules')
    reward_ids = fields.One2many('loyalty.reward', 'loyalty_program_id', string='Rewards')


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'

    name = fields.Char(index=True, required=True, help="An internal identification for this loyalty program rule")
    loyalty_program_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The Loyalty Program this exception belongs to')
    rule_type = fields.Selection((('product', 'Product'), ('category', 'Category')), old_name='type', required=True, default='product', help='Does this rule affects products, or a category of products ?')
    product_id = fields.Many2one('product.product', string='Target Product',  help='The product affected by the rule')
    category_id = fields.Many2one('pos.category', string='Target Category', help='The category affected by the rule')
    cumulative = fields.Boolean(help='The points won from this rule will be won in addition to other rules')
    pp_product = fields.Float(string='Points per product', help='How many points the product will earn per product ordered')
    pp_currency = fields.Float(string='Points per currency', help='How many points the product will earn per value sold')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'

    name = fields.Char(index=True, required=True, help='An internal identification for this loyalty reward')
    loyalty_program_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The Loyalty Program this reward belongs to')
    minimum_points = fields.Float(help='The minimum amount of points the customer must have to qualify for this reward')
    reward_type = fields.Selection((('gift', 'Gift'), ('discount', 'Discount'), ('resale', 'Resale')), old_name='type', required=True, help='The type of the reward')
    gift_product_id = fields.Many2one('product.product', string='Gift Product', help='The product given as a reward')
    point_cost = fields.Float(help='The cost of the reward')
    discount_product_id = fields.Many2one('product.product', string='Discount Product', help='The product used to apply discounts')
    discount = fields.Float(help='The discount percentage')
    point_product_id = fields.Many2one('product.product', string='Point Product', help='The product that represents a point that is sold by the customer')

    @api.one
    @api.constrains('reward_type', 'gift_product_id')
    def _check_gift_product(self):
        if self.reward_type == 'gift' and not self.gift_product_id:
            raise ValidationError(_('The gift product field is mandatory for gift rewards'))
        return True

    @api.one
    @api.constrains('reward_type', 'discount_product_id')
    def _check_discount_product(self):
        if self.reward_type == 'discount' and not self.discount_product_id:
            raise ValidationError(_('The discount product field is mandatory for discount rewards'))
        return True

    @api.one
    @api.constrains('reward_type', 'discount_product_id')
    def _check_point_product(self):
        if self.reward_type == 'resale' and not self.point_product_id:
            raise ValidationError(_('The point product field is mandatory for point resale rewards'))
        return True

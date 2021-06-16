# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _description = 'Loyalty Program'

    name = fields.Char(string='Loyalty Program Name', index=True, required=True, translate=True, help="An internal identification for the loyalty program configuration")
    points = fields.Float(string='Point per $ spent', help="How many loyalty points are given to the customer by sold currency")
    points_label = fields.Char(compute="_compute_points_label")
    rule_ids = fields.One2many('loyalty.rule', 'loyalty_program_id', string='Rules')
    reward_ids = fields.One2many('loyalty.reward', 'loyalty_program_id', string='Rewards')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)

    @api.depends('currency_id')
    def _compute_points_label(self):
        for program in self:
            program.points_label = _('Points per %s spent', program.currency_id.symbol)

    def _compute_program_amount(self, value, currency_to):
        self.ensure_one()
        return self.currency_id._convert(value, currency_to, self.company_id, fields.Date.today())


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _description = 'Loyalty Rule'

    name = fields.Char(index=True, required=True, help="An internal identification for this loyalty program rule")
    loyalty_program_id = fields.Many2one('loyalty.program', ondelete='cascade', string='Loyalty Program', help='The Loyalty Program this exception belongs to')
    points_quantity = fields.Float(string="Points per Unit")
    points_currency = fields.Float(string="Points per $ spent")
    points_currency_label = fields.Char(compute="_compute_points_currency_label")
    rule_domain = fields.Char()

    @api.depends('loyalty_program_id.currency_id')
    def _compute_points_currency_label(self):
        for rule in self:
            rule.points_currency_label = _('Points per %s spent', rule.loyalty_program_id.currency_id.symbol)


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['reward.mixin']
    _description = 'Loyalty Reward'

    name = fields.Char(index=True, required=True, help='An internal identification for this loyalty reward')
    loyalty_program_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The Loyalty Program this reward belongs to')
    minimum_points = fields.Float(help='The minimum amount of points the customer must have to qualify for this reward')
    reward_type = fields.Selection(required=True, help='The type of the reward', default="product")
    point_cost = fields.Float(string='Reward Cost', help="If the reward is a gift, that's the cost of the gift in points. If the reward type is a discount that's the cost in point per currency (e.g. 1 point per $)")
    discount_product_id = fields.Many2one('product.product', string='Discount Product', help='The product used to apply discounts')
    minimum_amount = fields.Float(string="Minimum Order Amount")
    currency_id = fields.Many2one(string="Currency", related='loyalty_program_id.currency_id', readonly=True)

    @api.constrains('reward_type', 'reward_product_id')
    def _check_gift_product(self):
        if self.filtered(lambda reward: reward.reward_type == 'product' and not reward.reward_product_id):
            raise ValidationError(_('The gift product field is mandatory for gift rewards'))

    @api.model
    def create(self, vals):
        reward = super().create(vals)
        if reward.reward_type == 'discount' and not vals.get('discount_product_id'):
            reward._create_discount_product()
        return reward

    def write(self, vals):
        res = super().write(vals)
        for reward in self.filtered(lambda reward: reward.reward_type == 'discount'):
            if not reward.discount_product_id:
                reward._create_discount_product()
            elif 'display_name' in vals:
                reward.discount_product_id.write({'name': self[0].display_name})
        return res

    def _get_discount_product_values(self):
        return {
            'name': self.display_name,
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': 0, #Do not set a high value to avoid issue with coupon code
        }

    def _create_discount_product(self):
        self.ensure_one()
        values = self._get_discount_product_values()
        discount_product_id = self.env['product.product'].create(values)
        self.write({'discount_product_id': discount_product_id.id})

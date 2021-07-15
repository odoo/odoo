# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CouponReward(models.Model):
    _name = 'coupon.reward'
    _description = "Coupon Reward"
    _rec_name = 'reward_description'

    # VFE FIXME multi company
    """Rewards are not restricted to a company...
    You could have a reward_product_id limited to a specific company A.
    But still use this reward as reward of a program of company B...
    """
    reward_description = fields.Char('Reward Description')
    reward_type = fields.Selection([
        ('discount', 'Discount'),
        ('product', 'Free Product'),
        ], string='Reward Type', default='discount',
        help="Discount - Reward will be provided as discount.\n" +
        "Free Product - Free product will be provide as reward \n" +
        "Free Shipping - Free shipping will be provided as reward (Need delivery module)")
    # Product Reward
    reward_product_id = fields.Many2one('product.product', string="Free Product",
        help="Reward Product")
    reward_product_quantity = fields.Integer(string="Quantity", default=1, help="Reward product quantity")
    # Discount Reward
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount')], default="percentage",
        help="Percentage - Entered percentage discount will be provided\n" +
        "Amount - Entered fixed amount discount will be provided")
    discount_percentage = fields.Float(string="Discount", default=10,
        help='The discount in percentage, between 1 and 100')
    discount_apply_on = fields.Selection([
        ('on_order', 'On Order'),
        ('cheapest_product', 'On Cheapest Product'),
        ('specific_products', 'On Specific Products')], default="on_order",
        help="On Order - Discount on whole order\n" +
        "Cheapest product - Discount on cheapest product of the order\n" +
        "Specific products - Discount on selected specific products")
    discount_specific_product_ids = fields.Many2many('product.product', string="Products",
        help="Products that will be discounted if the discount is applied on specific products")
    discount_max_amount = fields.Float(default=0,
        help="Maximum amount of discount that can be provided")
    discount_fixed_amount = fields.Float(string="Fixed Amount", help='The discount in fixed amount')
    reward_product_uom_id = fields.Many2one(related='reward_product_id.product_tmpl_id.uom_id', string='Unit of Measure', readonly=True)
    discount_line_product_id = fields.Many2one('product.product', string='Reward Line Product', copy=False,
        help="Product used in the sales order to apply the discount. Each coupon program has its own reward product for reporting purpose")

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        if self.filtered(lambda reward: reward.discount_type == 'percentage' and (reward.discount_percentage < 0 or reward.discount_percentage > 100)):
            raise ValidationError(_('Discount percentage should be between 1-100'))

    def name_get(self):
        """
        Returns a complete description of the reward
        """
        result = []
        for reward in self:
            reward_string = ""
            if reward.reward_type == 'product':
                reward_string = _("Free Product - %s", reward.reward_product_id.name)
            elif reward.reward_type == 'discount':
                if reward.discount_type == 'percentage':
                    reward_percentage = str(reward.discount_percentage)
                    if reward.discount_apply_on == 'on_order':
                        reward_string = _("%s%% discount on total amount", reward_percentage)
                    elif reward.discount_apply_on == 'specific_products':
                        if len(reward.discount_specific_product_ids) > 1:
                            reward_string = _("%s%% discount on products", reward_percentage)
                        else:
                            reward_string = _(
                                "%(percentage)s%% discount on %(product_name)s",
                                percentage=reward_percentage,
                                product_name=reward.discount_specific_product_ids.name
                            )
                    elif reward.discount_apply_on == 'cheapest_product':
                        reward_string = _("%s%% discount on cheapest product", reward_percentage)
                elif reward.discount_type == 'fixed_amount':
                    program = self.env['coupon.program'].search([('reward_id', '=', reward.id)])
                    reward_string = _(
                        "%(amount)s %(currency)s discount on total amount",
                        amount=reward.discount_fixed_amount,
                        currency=program.currency_id.name
                    )
            result.append((reward.id, reward_string))
        return result

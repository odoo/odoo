# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LoyaltyWebsiteReward(models.Model):
    _name = 'loyalty.website.reward'
    _description = 'Loyalty Website Reward'

    name = fields.Char(index=True, required=True, help='An internal identification for this loyalty reward')
    loyalty_program_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The Loyalty Program this reward belongs to')
    gift_card_product_id = fields.Many2one('product.product', required=True, string='Gift Card', help='The gift card given as a reward')
    point_cost = fields.Float(default=100.0, string='Reward Cost', help="Cost of the gift card in points")
    currency_id = fields.Many2one('res.currency', readonly=True, related='gift_card_product_id.currency_id')
    initial_amount = fields.Float(readonly=True, related='gift_card_product_id.list_price')
    validity = fields.Integer(required=True, default=365, string="Validity (days)", help="Number of days during which the card remains valid")

    @api.constrains('gift_card_product_id')
    def _check_gift_product(self):
        if self.filtered(lambda reward: reward.gift_card_product_id.detailed_type != 'gift'):
            raise ValidationError(_('The gift card product field must be a gift card'))

    def _redeem_gift_card(self, website_id):
        self.ensure_one()
        if self.env.user.loyalty_points < self.point_cost:
            raise UserError(_('Insufficient points'))
        self.env.user.loyalty_points = self.env.user.loyalty_points - self.point_cost
        gift_card_id = self.env['gift.card'].sudo().create({
            'company_id': self.env.company.id,
            'currency_id': self.currency_id.id,
            'initial_amount': self.initial_amount,
            'expired_date': fields.Date.add(fields.Date.today(), days=self.validity),
        })
        reward_id = self.env['loyalty.website.redeemed.reward'].sudo().create({
            'partner_id': self.env.user.partner_id.id,
            'website_id': website_id.id,
            'name': self.name,
            'point_used': self.point_cost,
            'gift_card_id': gift_card_id.id,
        })
        reward_id._send_gift_card_mail()
        return gift_card_id

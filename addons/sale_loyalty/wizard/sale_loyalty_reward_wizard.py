# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleLoyaltyRewardWizard(models.TransientModel):
    _name = 'sale.loyalty.reward.wizard'
    _description = 'Sale Loyalty - Reward Selection Wizard'

    order_id = fields.Many2one('sale.order', default=lambda self: self.env.context.get('active_id'), required=True)

    reward_ids = fields.Many2many('loyalty.reward', compute='_compute_claimable_reward_ids')
    selected_reward_id = fields.Many2one('loyalty.reward', domain="[('id', 'in', reward_ids)]")
    # In case of multi_product reward
    multi_product_reward = fields.Boolean(related='selected_reward_id.multi_product')
    reward_product_ids = fields.Many2many(related='selected_reward_id.reward_product_ids')
    selected_product_id = fields.Many2one('product.product', domain="[('id', 'in', reward_product_ids)]",
        compute='_compute_selected_product_id', readonly=False, store=True,)

    @api.depends('order_id')
    def _compute_claimable_reward_ids(self):
        for wizard in self:
            if not wizard.order_id:
                wizard.reward_ids = False
            else:
                claimable_reward = wizard.order_id._get_claimable_rewards()
                reward_ids = self.env['loyalty.reward']
                for rewards in claimable_reward.values():
                    reward_ids |= rewards
                wizard.reward_ids = reward_ids

    @api.depends('reward_product_ids')
    def _compute_selected_product_id(self):
        for wizard in self:
            if not wizard.selected_reward_id.reward_type == 'product':
                wizard.selected_product_id = False
            else:
                wizard.selected_product_id = wizard.reward_product_ids[:1]

    def action_apply(self):
        self.ensure_one()
        if not self.selected_reward_id:
            raise ValidationError(_('No reward selected.'))
        claimable_rewards = self.order_id._get_claimable_rewards()
        selected_coupon = False
        for coupon, rewards in claimable_rewards.items():
            if self.selected_reward_id in rewards:
                selected_coupon = coupon
                break
        if not selected_coupon:
            raise ValidationError(_('Coupon not found while trying to add the following reward: %s', self.selected_reward_id.description))
        self.order_id._apply_program_reward(self.selected_reward_id, coupon, product=self.selected_product_id)
        self.order_id._update_programs_and_rewards()
        return True

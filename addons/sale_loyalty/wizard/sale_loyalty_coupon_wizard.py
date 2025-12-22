# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError

class SaleLoyaltyCouponWizard(models.TransientModel):
    _name = 'sale.loyalty.coupon.wizard'
    _description = 'Sale Loyalty - Apply Coupon Wizard'

    order_id = fields.Many2one('sale.order', default=lambda self: self.env.context.get('active_id'), required=True)

    coupon_code = fields.Char(required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.order_id:
            raise ValidationError(_('Invalid sales order.'))
        status = self.order_id._try_apply_code(self.coupon_code)
        if 'error' in status:
            raise ValidationError(status['error'])
        all_rewards = self.env['loyalty.reward']
        for rewards in status.values():
            all_rewards |= rewards
        action = self.env['ir.actions.actions']._for_xml_id('sale_loyalty.sale_loyalty_reward_wizard_action')
        action['context'] = {
            'active_id': self.order_id.id,
            'default_reward_ids': all_rewards.ids,
        }
        return action

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    reward_type = fields.Selection(
        selection_add=[('shipping', 'Free Shipping')],
        ondelete={'shipping': 'set default'})

    def _compute_description(self):
        shipping_rewards = self.filtered(lambda r: r.reward_type == 'shipping')
        super(LoyaltyReward, self - shipping_rewards)._compute_description()
        shipping_rewards.description = _('Free shipping')
        for reward in shipping_rewards:
            if reward.discount_max_amount:
                format_string = '%(amount)g %(symbol)s'
                if reward.currency_id.position == 'before':
                    format_string = '%(symbol)s %(amount)g'
                formatted_amount = format_string % {'amount': reward.discount_max_amount, 'symbol': reward.currency_id.symbol}
                reward.description += _(' (Max %s)', formatted_amount)

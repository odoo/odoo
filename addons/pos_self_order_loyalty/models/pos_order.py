# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, Command, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'
    _name = 'pos.order'

    @api.model
    def _verify_reward_validity(self, pos_config, order, line_data, product_id):
        """Check that a claimed reward line is legitimate.

        Points cost and card balance are re-derived from the saved order at payment time
        (see PosOrder._process_loyalty / LoyaltyReward._get_pos_points_cost), so this only
        guards against a forged reward_id/product_id/card_id combination on a public
        self-order payload, not the exact monetary amount of the reward.

        :return: (reward, card) when the combination can be trusted, (False, False) otherwise.
        """
        reward = pos_config.env['loyalty.reward'].browse(line_data.get('reward_id')).exists()
        if not reward or reward.program_id not in pos_config._get_program_ids():
            return False, False

        if reward.reward_type == 'product':
            if product_id not in reward.reward_product_ids.ids:
                return False, False
        elif product_id != reward.discount_line_product_id.id:
            return False, False

        card = pos_config.env['loyalty.card']
        if line_data.get('card_id'):
            card = card.browse(line_data['card_id']).exists()
            # A card reserved for a partner (nominative programs, e.g. loyalty cards tied to a
            # customer) may only be spent on an order made for that same partner. Anonymous
            # cards (gift cards, unassigned coupons) have no partner_id and are usable by
            # whoever knows their id/code, the same trust model as a physical gift card.
            if not card or (card.partner_id and card.partner_id.id != order.get('partner_id')):
                return False, False

        return reward, card

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        result = super()._check_pos_order_lines(pos_config, order, line, fiscal_position_id)
        if not result or result[0] not in (Command.CREATE, Command.UPDATE):
            return result

        line_data = line[2]
        if not line_data.get('is_reward_line'):
            return result

        reward, card = self._verify_reward_validity(pos_config, order, line_data, result[2]['product_id'])
        if not reward:
            raise UserError(_("Invalid reward"))

        result[2].update({
            'is_reward_line': True,
            'reward_id': reward.id,
            'card_id': card.id,
            # A free-product reward's price is always 0; a discount line's amount is only
            # ever verified for discount_mode == 'per_point' (see _get_pos_points_cost), so it
            # is left as sent here and re-derived/bounded against the card balance at payment
            # time by _process_loyalty(). points_cost itself is always overwritten there too.
            'price_unit': 0.0 if reward.reward_type == 'product' else result[2]['price_unit'],
            'points_cost': 0.0,
            'tax_ids': [] if card.program_type in ['gift_card', 'ewallet'] else result[2]['tax_ids'],
        })
        return result

    def _compute_line_price(self, line, price=False):
        # recompute_prices() reprices every non-combo/delivery/tip line from the pricelist,
        # which would overwrite a reward line's price (0 for a free product, the validated
        # discount amount for a discount line) with the reward/discount product's own price.
        # The price was already fixed and validated in _check_pos_order_lines, so only the
        # subtotals (tax-dependent) need recomputing here.
        if line.is_reward_line:
            self._compute_line_subtotals(line)
            return
        super()._compute_line_price(line, price=price)

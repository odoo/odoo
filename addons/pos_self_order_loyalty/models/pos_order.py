# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, Command, _
from odoo.exceptions import UserError
from odoo.addons.pos_self_order_loyalty.models.res_partner import SelfOrderIdentificationExpired


class PosOrder(models.Model):
    _inherit = 'pos.order'
    _name = 'pos.order'

    @api.model
    def _check_pos_order(self, pos_config, order, device_type, table=None):
        """A partner on a public self-order payload must be backed by an identification token.

        Once an order carries a partner, later syncs keeping that same partner are trusted:
        it was verified when it was set.
        """
        partner_id = order.get('partner_id')
        if partner_id:
            existing_order = pos_config.env['pos.order']
            if isinstance(order.get('id'), int) and order.get('uuid'):
                existing_order = existing_order.search([('id', '=', order['id']), ('uuid', '=', order['uuid'])])
            if existing_order.partner_id.id != partner_id and not pos_config.env['res.partner']._get_partner_from_self_order_token(
                pos_config, partner_id, order.get('partner_token'),
            ):
                raise SelfOrderIdentificationExpired(_("Your identification has expired, please identify yourself again."))
        return super()._check_pos_order(pos_config, order, device_type, table)

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

        if card.program_type in ['gift_card', 'ewallet']:
            tax_ids = []
        elif reward.reward_type == 'discount':
            # The frontend splits a discount in one line per tax group of the discounted lines
            # (see LoyaltyReward.getRewardLineValues), so its taxes are the ones of those lines,
            # not the discount product's. They are checked against the order's lines once all
            # lines exist, in _check_self_order_discount_rewards().
            requested_tax_ids = [id for id in line_data.get('tax_ids') or [] if isinstance(id, int)]
            tax_ids = pos_config.env['account.tax'].browse(requested_tax_ids).exists().ids
        else:
            tax_ids = result[2]['tax_ids']

        result[2].update({
            'is_reward_line': True,
            'reward_id': reward.id,
            'card_id': card.id,
            # A free-product reward's price is always 0. A discount line's amount is left as
            # sent here and bounded server-side by _check_self_order_discount_rewards() once
            # the order's lines are priced. points_cost is always overwritten by
            # _process_loyalty() at payment time.
            'price_unit': 0.0 if reward.reward_type == 'product' else result[2]['price_unit'],
            'points_cost': 0.0,
            'tax_ids': tax_ids,
        })
        return result

    def recompute_prices(self):
        super().recompute_prices()
        self._check_self_order_discount_rewards()

    def _get_self_order_discountable_amounts(self):
        """Tax-included amount of every line a discount reward may apply to.

        Mirrors LoyaltyReward.getDiscountApplicableLines: tip, service fee and reward lines
        are excluded, and a combo is considered as a whole through its parent line, its
        amount being the sum of its (server-priced) children.

        :return: {top-level line: tax-included amount}
        """
        excluded_products = self.config_id.tip_product_id | self.preset_id.service_fee_product_id
        amounts = defaultdict(float)
        for line in self.lines.filtered(lambda l: not l.combo_line_ids and not l.is_reward_line):
            top_line = line.combo_parent_id or line
            if top_line.product_id not in excluded_products:
                amounts[top_line] += line.price_subtotal_incl
        return {line: amount for line, amount in amounts.items() if line.qty > 0 and amount > 0}

    def _get_self_order_max_discount(self, reward, discountable_amounts):
        """Highest tax-included amount `reward` can legitimately discount on this order.

        Upper bound of LoyaltyReward.getRewardLineValuesDiscount: it ignores what earlier
        rewards already consumed, which is covered by the order-wide check instead.
        """
        if reward.discount_applicability in ('specific', 'cheapest'):
            products = self.env['product.product'].browse(
                line.product_id.id for line in discountable_amounts
            ).filtered_domain(reward._get_discount_product_domain())
            discountable_amounts = {
                line: amount for line, amount in discountable_amounts.items()
                if line.product_id in products
            }
        if not discountable_amounts:
            return 0.0
        if reward.discount_applicability == 'cheapest':
            discountable = min(amount / line.qty for line, amount in discountable_amounts.items())
        else:
            discountable = sum(discountable_amounts.values())

        if reward.discount_mode == 'percent':
            max_discount = discountable * reward.discount / 100
        elif reward.discount_mode == 'per_order':
            max_discount = reward.discount
        else:
            # per_point: the points it costs are re-derived from the amount and checked
            # against the card balance by _process_loyalty()
            max_discount = discountable
        return min(max_discount, discountable, reward.discount_max_amount or max_discount)

    def _check_self_order_discount_rewards(self):
        """Refuse discount reward lines whose amount a genuine self-order client can't produce.

        A discount line's price comes from the public payload, so it is bounded here against
        the server-priced lines it may apply to.
        """
        self.ensure_one()
        reward_lines = self.lines.filtered(
            lambda l: l.is_reward_line and l.reward_id.reward_type == 'discount'
        )
        if not reward_lines:
            return

        currency = self.currency_id
        if any(currency.compare_amounts(line.price_unit, 0) > 0 for line in reward_lines):
            raise UserError(_("Invalid reward discount"))

        discountable_amounts = self._get_self_order_discountable_amounts()
        discounted_lines = self.lines.filtered(lambda l: (l.combo_parent_id or l) in discountable_amounts)
        if reward_lines.tax_ids_after_fiscal_position - discounted_lines.tax_ids_after_fiscal_position:
            raise UserError(_("Invalid reward discount"))

        total_discount = 0.0
        # Payment programs (gift card, eWallet) are bounded by the card balance in _process_loyalty()
        for reward, lines in reward_lines.filtered(lambda l: not l.reward_id.program_id.is_payment_program).grouped('reward_id').items():
            discount = -sum(lines.mapped('price_subtotal_incl'))
            max_discount = self._get_self_order_max_discount(reward, discountable_amounts)
            # The frontend rounds each tax group's line separately, tolerate it
            if currency.compare_amounts(discount, max_discount + currency.rounding * len(lines)) > 0:
                raise UserError(_("Invalid reward discount"))
            total_discount += discount

        max_total_discount = sum(discountable_amounts.values())
        if currency.compare_amounts(total_discount, max_total_discount) > 0 or currency.compare_amounts(self.amount_total, 0) < 0:
            raise UserError(_("Invalid reward discount"))

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

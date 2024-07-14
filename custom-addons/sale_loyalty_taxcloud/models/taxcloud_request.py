# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_account_taxcloud.models import taxcloud_request


def subn(price, discount):
    """
    :param price: positive number
    :param discount: negative number
    :return: natural subtraction of the discount to the price, and the remainder
    """
    return max(price + discount, 0), min(price + discount, 0)

class TaxCloudRequest(taxcloud_request.TaxCloudRequest):
    """We apply the discount directly on the target lines.
       We send the corrected lines to Taxcloud, as intended.
       This gives us the taxes per line, as before, so we don't need to change anything else.
    """

    def _process_lines(self, lines):
        self._apply_discount_on_lines(lines)
        return super(TaxCloudRequest, self)._process_lines(lines)

    def _apply_discount_on_lines(self, lines):
        """We need to sort the discounts to apply first line-specific discounts first.
           Then we apply the discount evenly, and the rest sequentially.
           In the case there is still a remainder, it is ignored,
           as it would be a negative SO/invoice without taxes anyway.
        """
        for line in lines:
            line.price_taxcloud = line.price_unit

        discounts_to_apply = lines.filtered(lambda l: l.reward_id)
        sorted_discounts = discounts_to_apply.sorted(key=self._rank_discount_line)

        for discount_line in sorted_discounts:
            discountable_lines = self._get_discountable_lines(discount_line, lines)
            discount_sum = discount_line._get_qty() * discount_line.price_unit
            remainder = self._apply_evenly(discount_sum, discountable_lines)
            remainder = self._apply_sequentially(remainder, discountable_lines)
            if remainder:  # in case some product-specific discount could not be applied, backup on all lines
                all_discountable_lines = lines.filtered(lambda l: l.price_taxcloud > 0 and l._get_qty() > 0)
                remainder = self._apply_evenly(remainder, all_discountable_lines)
                remainder = self._apply_sequentially(remainder, all_discountable_lines)

    def _apply_evenly(self, discount, lines):
        remainder = 0
        sum_lines = sum(l.price_taxcloud * l._get_qty() for l in lines)
        if sum_lines:
            for line in lines:
                ratio = (line._get_qty() * line.price_taxcloud) / sum_lines
                line_discount = (ratio * discount) / line._get_qty()
                line.price_taxcloud, remains = subn(line.price_taxcloud, line_discount)
                remainder += remains * line._get_qty()
        else:
            remainder = discount
        return remainder

    def _apply_sequentially(self, discount, lines):
        for line in lines:
            line_discount = discount / line._get_qty()
            line.price_taxcloud, remains = subn(line.price_taxcloud, line_discount)
            discount = remains * line._get_qty()
        return discount

    def _rank_discount_line(self, line):
        return [
            line.reward_id.reward_type != 'product',
            line.reward_id.discount_applicability != 'specific',
            line.reward_id.discount_applicability != 'cheapest',
            line.reward_id.discount_mode not in ('per_point', 'per_order'),
        ]

    def _get_discountable_lines(self, discount_line, lines):
        reward = discount_line.reward_id
        lines = lines.filtered(lambda l: l.price_taxcloud > 0 and l._get_qty() > 0)
        if reward.reward_type == 'product':
            lines = lines.filtered(lambda l: l.product_id == reward.reward_product_id and not l.is_reward_line)
        elif reward.discount_applicability == 'specific':
            domain = reward._get_discount_product_domain()
            lines = lines.filtered(lambda l: l.product_id.filtered_domain(domain))
        elif reward.discount_applicability == 'cheapest':
            lines = self._get_cheapest_line(lines)
        return lines

    def _get_cheapest_line(self, lines):
        return min(lines, key=lambda l: l['price_taxcloud']) if lines else lines

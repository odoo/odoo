# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from . import common


def record_powerset(records):
    def flatten_subset(subset):
        if len(list(subset)):
            recordset = subset[0]
            for record in subset[1:]:
                recordset += record
        else:
            recordset = records.browse()
        return recordset

    powerset = list()
    for n in range(len(records) + 1):
        for subset in itertools.combinations(records, n):
            powerset.append(flatten_subset(subset))
    return powerset


class TestSaleCouponPriceTaxCloud(common.TestSaleCouponTaxCloudCommon):

    def test_total(self):
        """Test that the sum of TaxCloud is equal to the order total
           (with applied discounts), for all possible sets of discounts.
           This is the most important coherency issue.
           So we don't test how coupon are applied, just that the result of our
           computations match what is obtained from the lines.
        """
        TaxCloud = self.order._get_TaxCloudRequest("id", "api_key")

        for applied_discounts in record_powerset(self.all_programs):
            self.order.applied_coupon_ids = applied_discounts.coupon_ids
            self.order._update_programs_and_rewards()
            lines = self.order.order_line
            TaxCloud._apply_discount_on_lines(lines)
            sum_taxcloud = sum(lines.filtered(lambda l: l.price_taxcloud > 0)
                               .mapped(lambda l: l.price_taxcloud * l.product_uom_qty))

            self.assertEqual(sum_taxcloud, self.order.amount_total)

    def test_free_product(self):
        """Test that taxcloud is working correctly with the addition of
           the free product reward.
        """
        TaxCloud = self.order._get_TaxCloudRequest("id", "api_key")

        self._apply_promo_code(self.order, self.program_free_product_C.coupon_ids.code)

        discount_line = self.order.order_line.filtered('reward_id')
        self.assertEqual(discount_line.price_unit, -10)
        self.assertEqual(discount_line.product_uom_qty, 1)

        lines = self.order.order_line
        TaxCloud._apply_discount_on_lines(lines)

        line_C = lines.filtered(lambda l: l.product_id == self.product_C)
        self.assertEqual(line_C.price_taxcloud, 0)

        other_lines = lines.filtered(lambda l: l.price_taxcloud > 0) - line_C
        for line in other_lines:
            self.assertAlmostEqual(line.price_taxcloud, line.price_unit)

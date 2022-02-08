# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleCouponMultiCompany(TestSaleCouponCommon):

    def setUp(self):
        super(TestSaleCouponMultiCompany, self).setUp()

        self.company_a = self.env.company
        self.company_b = self.env['res.company'].create(dict(name="TEST"))

        self.immediate_promotion_program_c2 = self.env['coupon.program'].create({
            'name': 'Buy A + 1 B, 1 B are free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'reward_product_id': self.product_B.id,
            'rule_products_domain': "[('id', 'in', [%s])]" % (self.product_A.id),
            'active': True,
            'company_id': self.company_b.id,
        })

    def test_applicable_programs(self):

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()

        def _get_applied_programs(order):
            # temporary copy of sale_order._get_applied_programs
            # to ensure each commit stays independent
            # can be later removed and replaced in master.
            return order.code_promo_program_id + order.no_code_promo_program_ids + order.applied_coupon_ids.mapped('program_id')

        self.assertNotIn(self.immediate_promotion_program_c2, order._get_applicable_programs())
        self.assertNotIn(self.immediate_promotion_program_c2, _get_applied_programs(order))

        order_b = self.env["sale.order"].create({
            'company_id': self.company_b.id,
            'partner_id': order.partner_id.id,
        })
        order_b.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.assertNotIn(self.immediate_promotion_program, order_b._get_applicable_programs())

        order_b.recompute_coupon_lines()
        self.assertIn(self.immediate_promotion_program_c2, _get_applied_programs(order_b))
        self.assertNotIn(self.immediate_promotion_program, _get_applied_programs(order_b))

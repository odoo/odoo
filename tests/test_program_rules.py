# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.fields import Date

class TestProgramRules(TestSaleCouponCommon):
    # Test all the validity rules to allow a customer to have a reward.
    # The check based on the products is already done in the basic operations test

    def test_program_rules_partner_based(self):
        # Test case: Based on the partners domain

        self.immediate_promotion_program.write({'rule_partners_domain': "[('id', 'in', [%s])]" % (self.steve.id)})

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
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as the partner is correct, the discount is not created")

        order = self.env['sale.order'].create({'partner_id': self.env.ref('base.res_partner_1').id})
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
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied, the discount is created")

    def test_program_rules_minimum_purchased_amount(self):
        # Test case: Based on the minimum purchased

        self.immediate_promotion_program.write({
            'rule_minimum_amount': 1000.0,
            'rule_minimum_amount_tax_inclusion': 'tax_excluded'
        })

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
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied as the purchased amount is not enough")

        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as the purchased amount is enough")

    def test_program_rules_validity_dates_and_uses(self):
        # Test case: Based on the validity dates and the number of allowed uses

        self.immediate_promotion_program.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=7))),
            'rule_date_to': Date.to_string((datetime.now() - timedelta(days=2))),
            'maximum_use_number': 1,
        })

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
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=7))),
            'rule_date_to': Date.to_string((datetime.now() + timedelta(days=2))),
        })
        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as we're between the validity dates")
        order = self.env['sale.order'].create({'partner_id': self.env.ref('base.res_partner_1').id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied as the number of uses is exceeded")

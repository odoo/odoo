# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestSaleCouponMultiCompany(TestSaleCouponCommon):

    def setUp(self):
        super(TestSaleCouponMultiCompany, self).setUp()

        self.company_a = self.env.company
        self.company_b = self.env['res.company'].create(dict(name="TEST"))

        self.immediate_promotion_program_c2 = self.env['loyalty.program'].create({
            'name': 'Buy A + 1 B, 1 B are free',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'company_id': self.company_b.id,
            'rule_ids': [(0, 0, {
                'product_ids': self.product_A,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_B.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })

    def _get_applicable_programs(self, order):
        return self.env['loyalty.program'].browse(p.id for p in order._get_applicable_program_points())

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
        order._update_programs_and_rewards()

        self.assertNotIn(self.immediate_promotion_program_c2, self._get_applicable_programs(order))
        self.assertNotIn(self.immediate_promotion_program_c2, order._get_applied_programs())

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
        self.assertNotIn(self.immediate_promotion_program, self._get_applicable_programs(order_b))
        order_b._update_programs_and_rewards()
        self.assertIn(self.immediate_promotion_program_c2, order_b._get_applied_programs())
        self.assertNotIn(self.immediate_promotion_program, order_b._get_applied_programs())

    def test_applicable_programs_on_branch(self):
        # create a branch
        branch_a = self.env['res.company'].create(
            {'name': 'Branch A', 'parent_id': self.company_a.id}
        )

        # create an order
        order = self.env['sale.order'].create(
            {'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'name': '1 Product A',
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'name': '2 Product B',
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                })
            ],
            'company_id': branch_a.id,
            'partner_id': self.partner.id
            }
        )

        order._update_programs_and_rewards()
        self.assertIn(self.immediate_promotion_program, order._get_applied_programs())

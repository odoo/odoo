# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command
from odoo.exceptions import ValidationError

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


class TestSaleCouponCommon(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # set currency to not rely on demo data and avoid possible race condition
        cls.currency_ratio = 1.0
        pricelist = cls.env.ref('product.list0')
        pricelist.currency_id = cls._setup_currency(cls.currency_ratio)

        # Disable noisy pricelist (aka demo data Benelux)
        cls.env.user.partner_id.write({
            'property_product_pricelist': pricelist.id,
        })
        (cls.env['product.pricelist'].search([]) - pricelist).write({'active': False})

        # Set all the existing programs to active=False to avoid interference
        cls.env['loyalty.program'].search([]).sudo().write({'active': False})

        # create partner for sale order.
        cls.steve = cls.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.steve.id
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Taxes
        cls.tax_15pc_excl = cls.env['account.tax'].create({
            'name': "Tax 15%",
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
        })

        cls.tax_10pc_incl = cls.env['account.tax'].create({
            'name': "10% Tax incl",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
        })

        cls.tax_10pc_base_incl = cls.env['account.tax'].create({
            'name': "10% Tax incl base amount",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })

        cls.tax_10pc_excl = cls.env['account.tax'].create({
            'name': "10% Tax excl",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': False,
        })

        cls.tax_20pc_excl = cls.env['account.tax'].create({
            'name': "20% Tax excl",
            'amount_type': 'percent',
            'amount': 20,
            'price_include': False,
        })

        cls.tax_group = cls.env['account.tax'].create({
            'name': "tax_group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((cls.tax_10pc_incl + cls.tax_10pc_base_incl).ids)],
        })

        #products
        cls.product_A = cls.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_15pc_excl.id])],
        })

        cls.product_B = cls.env['product.product'].create({
            'name': 'Product B',
            'list_price': 5,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_15pc_excl.id])],
        })

        cls.product_C = cls.env['product.product'].create({
            'name': 'Product C',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [])],
        })

        cls.product_D = cls.env['product.product'].create({
            'name': 'Product D',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_group.id])],
        })

        cls.product_gift_card = cls.env['product.product'].create({
            'name': 'Gift Card 50',
            'detailed_type': 'service',
            'list_price': 50,
            'sale_ok': True,
            'taxes_id': False,
        })

        # Immediate Program By A + B: get B free
        # No Conditions
        cls.program_gift_card = cls.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'applies_on': 'future',
            'program_type': 'gift_card',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'product_ids': cls.product_gift_card,
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 1,
                'discount_mode': 'per_point',
                'discount_applicability': 'order',
            })]
        })
        cls.immediate_promotion_program = cls.env['loyalty.program'].create({
            'name': 'Buy A + 1 B, 1 B are free',
            'program_type': 'promotion',
            'applies_on': 'current',
            'company_id': cls.env.company.id,
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'product_ids': cls.product_A,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.product_B.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        cls.code_promotion_program = cls.env['loyalty.program'].create({
            'name': 'Buy 1 A + Enter code, 1 A is free',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'company_id': cls.env.company.id,
            'rule_ids': [(0, 0, {
                'product_ids': cls.product_A,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.product_A.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        cls.code_promotion_program_with_discount = cls.env['loyalty.program'].create({
            'name': 'Buy 1 C + Enter code, 10 percent discount on C',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'company_id': cls.env.company.id,
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'promotion_code_disc',
                'product_ids': cls.product_C,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })

    def _extract_rewards_from_claimable(self, status):
        rewards = self.env['loyalty.reward']
        for info in status.values():
            for reward_count in info['rewards']:
                rewards |= reward_count[0]

    def _apply_promo_code(self, order, code, no_reward_fail=True):
        status = order._try_apply_code(code)
        if 'error' in status:
            raise ValidationError(status['error'])
        if not status and no_reward_fail:
            # Can happen if global discount got filtered out in `_get_claimable_rewards`
            raise ValidationError('No reward to claim with this coupon')
        coupons = self.env['loyalty.card']
        rewards = self.env['loyalty.reward']
        for coupon, coupon_rewards in status.items():
            coupons |= coupon
            rewards |= coupon_rewards
        if len(coupons) == 1 and len(rewards) == 1:
            status = order._apply_program_reward(rewards, coupons)
            if 'error' in status:
                raise ValidationError(status['error'])

    def _claim_reward(self, order, program, coupon=False):
        if len(program.reward_ids) != 1:
            return False
        coupon = coupon or order.coupon_point_ids.coupon_id.filtered(lambda c: c.program_id == program)
        if len(coupon) != 1:
            return False
        status = order._apply_program_reward(program.reward_ids, coupon)
        return 'error' not in status

    def _auto_rewards(self, order, programs):
        order._update_programs_and_rewards()
        coupons_per_program = defaultdict(lambda: self.env['loyalty.card'])
        for coupon in order.coupon_point_ids.coupon_id:
            coupons_per_program[coupon.program_id] |= coupon
        for program in programs:
            if len(program.reward_ids) > 1 or len(coupons_per_program[program]) != 1 or not program.active:
                continue
            self._claim_reward(order, program, coupons_per_program[program])

class TestSaleCouponNumbersCommon(TestSaleCouponCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.largeCabinet = cls.env['product.product'].create({
            'name': 'Large Cabinet',
            'list_price': 320.0,
            'taxes_id': False,
        })
        cls.conferenceChair = cls.env['product.product'].create({
            'name': 'Conference Chair',
            'list_price': 16.5,
            'taxes_id': False,
        })
        cls.pedalBin = cls.env['product.product'].create({
            'name': 'Pedal Bin',
            'list_price': 47.0,
            'taxes_id': False,
        })
        cls.drawerBlack = cls.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 25.0,
            'taxes_id': False,
        })
        cls.largeMeetingTable = cls.env['product.product'].create({
            'name': 'Large Meeting Table',
            'list_price': 40000.0,
            'taxes_id': False,
        })

        cls.steve = cls.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
        })
        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.steve.id
        })

        cls.p1 = cls.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        cls.p2 = cls.env['loyalty.program'].create({
            'name': 'Buy 3 cabinets, get one for free',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': cls.largeCabinet,
                'reward_point_mode': 'unit',
                'minimum_qty': 3,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.largeCabinet.id,
                'reward_product_qty': 1,
                'required_points': 3,
            })],
        })
        cls.p3 = cls.env['loyalty.program'].create({
            'name': 'Buy 1 drawer black, get a free Large Meeting Table',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': cls.drawerBlack,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.largeMeetingTable.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        cls.discount_coupon_program = cls.env['loyalty.program'].create({
            'name': '$100 coupon',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'minimum_amount': 100,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 100,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        cls.all_programs = cls.env['loyalty.program'].search([])

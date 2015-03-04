# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta

from openerp import fields
from openerp.tests import common


class TestSaleCouponCommon(common.TransactionCase):

    def setUp(self):
        super(TestSaleCouponCommon, self).setUp()

        # Usefull models
        self.SaleApplicability = self.env['sale.applicability']
        self.SaleReward = self.env['sale.reward']
        self.SaleCoupon = self.env['sale.coupon']
        self.CouponProgram = self.env['sale.couponprogram']
        self.Partner = self.env['res.partner']
        self.Product = self.env['product.product']
        self.SaleOrder = self.env['sale.order']

        # create partner for sale order.
        self.partner_id = self.Partner.create({
            'name': 'Steve Bucknor',
            'email': 'steve_bucknor@odoo.com',
        })

        # create product with coupon type
        self.product_conference = self.Product.create({
            'name': 'National Conference',
            'type': 'service',
        })

        self.product_training = self.Product.create({
            'name': 'Functional Training',
            'type': 'service',
            'price_unit': 1000,
        })
        self.product_technical_training = self.Product.create({
            'name': 'Technical Training',
            'type': 'service',
            'price_unit': 1500,
        })

        # create coupon program
        self.couponprogram_1 = self.CouponProgram.create({
            'program_name': 'Buy 2 Get 1 Free',
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'poroduct',
            'validity_type': 'day',
            'validity_duration': 10,
            'product_id': self.product_conference.id,
            'product_quantity': 2,
            'reward_type': 'product',
            'reward_product_product_id': self.product_conference.id,
            'reward_quantity': 1,
        })

        self.couponprogram_2 = self.CouponProgram.create({
            'program_name': "10'%' Discount on Functional Training",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'poroduct',
            'validity_type': 'week',
            'validity_duration': 1,
            'product_id': self.product_conference.id,
            'product_quantity': 1,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount': 10,
            'reward_discount_on': 'specific_product',
            'reward_discount_on_product_id': self.product_training.id,
        })

        self.couponprogram_3 = self.CouponProgram.create({
            'program_name': "National Conference Free on Functional Training",
            'program_type': 'apply_immediately',
            'program_sequence': 2,
            'purchase_type': 'poroduct',
            'validity_type': 'month',
            'validity_duration': 10,
            'product_id': self.product_training.id,
            'product_quantity': 1,
            'reward_type': 'product',
            'reward_product_product_id': self.product_conference.id,
            'reward_quantity': 1,
        })

        self.couponprogram_4 = self.CouponProgram.create({
            'program_name': "100 off on Functional Training",
            'program_type': 'apply_immediately',
            'program_sequence': 3,
            'purchase_type': 'amount',
            'validity_type': 'day',
            'validity_duration': 15,
            'minimum_amount': 1000,
            'reward_type': 'discount',
            'reward_discount_type': 'amount',
            'reward_discount': 100,
            'reward_tax': 'tax_included',
        })

        self.couponprogram_5 = self.CouponProgram.create({
            'program_name': "10'%' off",
            'program_type': 'public_unique_code',
            'program_code': 'SC5657585',
            'program_sequence': 1,
            'purchase_type': 'amount',
            'date_from': date.today(),
            'date_to': date.today() + relativedelta(days=10),
            'minimum_amount': 0,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_on': 'cart',
            'reward_discount': 10,
        })

        self.couponprogram_6 = self.CouponProgram.create({
            'program_name': "30'%' on cheapest product",
            'program_type': 'public_unique_code',
            'program_code': 'SC5656565',
            'program_sequence': 1,
            'purchase_type': 'amount',
            'date_from': date.today(),
            'date_to': date.today() + relativedelta(days=10),
            'minimum_amount': 0,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_on': 'cheapest_product',
            'reward_discount': 30,
        })

        self.couponprogram_7 = self.CouponProgram.create({
            'program_name': "500 off",
            'program_type': 'generated_coupon',
            'program_sequence': 5,
            'purchase_type': 'amount',
            'validity_type': 'day',
            'validity_duration': 10,
            'minimum_amount': 0,
            'reward_type': 'discount',
            'reward_discount_type': 'amount',
            'reward_discount': 500,
            'reward_tax': 'tax_included',
        })

        self.couponprogram_8 = self.CouponProgram.create({
            'program_name': "Gift Vouchar",
            'program_type': 'apply_immediately',
            'program_sequence': 5,
            'purchase_type': 'amount',
            'validity_type': 'day',
            'validity_duration': 10,
            'minimum_amount': 2000,
            'reward_type': 'coupon',
            'reward_gift_coupon_id': self.couponprogram_7.id,
        })

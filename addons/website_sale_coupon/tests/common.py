# -*- coding: utf-8 -*-
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
        self.Category = self.env['product.category']
        self.reward_product = self.env.ref('website_sale_coupon.product_product_reward')

        # create partner for sale order.
        self.partner_id = self.Partner.create({
            'name': 'Steve Bucknor',
            'email': 'steve_bucknor@odoo.com',
        })

        self.category_beverage = self.Category.create({
            'name': 'Beverage',
        })

        #products
        self.product_mobile = self.Product.create({
            'name': 'Mobile',
            'type': 'service',
            'price': 100,
        })

        self.product_cover = self.Product.create({
            'name': 'Cover',
            'type': 'service',
            'price': 50,
        })

        self.product_pendrive = self.Product.create({
            'name': 'Pen drive',
            'type': 'service',
            'price': 60,
        })

        self.product_pendrive_cover = self.Product.create({
            'name': 'Pen drive cover',
            'type': 'service',
            'price': 20,
        })
        self.product_harddisk = self.Product.create({
            'name': 'hard disk',
            'type': 'service',
            'price': 50,
        })

        self.product_coca_cola = self.Product.create({
            'name': 'Coca cola',
            'type': 'service',
            'price': 20,
            'categ_id': self.category_beverage.id,
        })

        self.product_pepsi = self.Product.create({
            'name': 'Pepsi',
            'type': 'service',
            'price': 10,
            'categ_id': self.category_beverage.id,
        })

        self.couponprogram_1 = self.CouponProgram.create({
            'name': 'Buy 1 Mobile + get 1 cover free',
            'program_type': 'apply_immediately',
            'validity_type': 'day',
            'validity_duration': 15,
            'purchase_type': 'product',
            'product_id': self.product_mobile.id,
            'product_quantity': 1,
            'reward_type': 'product',
            'reward_product_product_id': self.product_cover.id,
            'reward_quantity': 1,
        })

        self.couponprogram_2 = self.CouponProgram.create({
            'name': "Buy 2 Hard disk + get 1 hard disk free",
            'program_type': 'apply_immediately',
            'purchase_type': 'product',
            'validity_type': 'day',
            'validity_duration': 15,
            'product_id': self.product_harddisk.id,
            'product_quantity': 2,
            'reward_type': 'product',
            'reward_product_product_id': self.product_harddisk.id,
            'reward_quantity': 1,
        })

        self.couponprogram_3 = self.CouponProgram.create({
            'name': "Buy any product of beverage category in 2 qty and get 5$ off",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'category',
            'product_category_id': self.category_beverage.id,
            'validity_type': 'day',
            'validity_duration': 15,
            'product_quantity': 2,
            'reward_type': 'discount',
            'reward_discount_type': 'amount',
            'reward_discount_amount': 2,
        })

        self.couponprogram_4 = self.CouponProgram.create({
            'name': "Purchase for 1000 and above + 10'%' off on cart",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'amount',
            'validity_type': 'day',
            'validity_duration': 15,
            'minimum_amount': 1000,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_percentage': 10,
            'reward_discount_on': 'cart'
        })

        self.couponprogram_5 = self.CouponProgram.create({
            'name': "Buy 1 pen drive and get 10'%' off on pen drive cover",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'product',
            'product_id': self.product_pendrive.id,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_on': 'specific_product',
            'reward_discount_on_product_id': self.product_pendrive_cover.id,
            'reward_discount_percentage': 10,
        })

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
        self.SaleGetCoupon = self.env['sale.get.coupon']
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

        self.product_shoe = self.Product.create({
            'name': 'Shoe',
            'type': 'service',
            'price': 100,
        })

        self.product_socks = self.Product.create({
            'name': 'Socks',
            'type': 'service',
            'price': 10,
        })

        self.product_laptop = self.Product.create({
            'name': 'Laptop',
            'type': 'service',
            'price': 100,
        })

        self.product_refrigerator = self.Product.create({
            'name': 'Refrigerator',
            'type': 'service',
            'price': 150,
        })

        self.product_iphone = self.Product.create({
            'name': 'iPhone',
            'type': 'service',
            'price': 150,
        })

        self.product_delivery_charge = self.Product.create({
            'name': 'Standard Delivery',
            'type': 'service',
            'price': 10.0,
            'is_delivery_charge_product': True,
        })

        self.couponprogram_1 = self.CouponProgram.create({
            'name': 'Buy 1 Mobile + get 1 cover free',
            'program_type': 'apply_immediately',
            'purchase_type': 'product',
            'product_id': self.product_mobile.id,
            'product_quantity': 1,
            'reward_type': 'product',
            'reward_product_product_id': self.product_cover.id,
            'reward_quantity': 1,
            'state': 'opened',
        })

        self.couponprogram_2 = self.CouponProgram.create({
            'name': "Buy 2 Hard disk + get 1 hard disk free",
            'program_type': 'apply_immediately',
            'purchase_type': 'product',
            'product_id': self.product_harddisk.id,
            'product_quantity': 2,
            'reward_type': 'product',
            'reward_product_product_id': self.product_harddisk.id,
            'reward_quantity': 1,
            'state': 'opened',
        })

        self.couponprogram_3 = self.CouponProgram.create({
            'name': "Buy any product of beverage category in 2 qty and get 5$ off",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'category',
            'product_category_id': self.category_beverage.id,
            'product_quantity': 2,
            'reward_type': 'discount',
            'reward_discount_type': 'amount',
            'reward_discount_amount': 2,
            'state': 'opened',
        })

        self.couponprogram_4 = self.CouponProgram.create({
            'name': "Purchase for 100 and above + 10'%' off on cart",
            'program_type': 'apply_immediately',
            'program_sequence': 1,
            'purchase_type': 'amount',
            'minimum_amount': 1500,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_percentage': 10,
            'reward_discount_on': 'cart',
            'state': 'opened',
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
            'state': 'opened',
        })

        self.couponprogram_6 = self.CouponProgram.create({
            'name': 'PUC Buy 1 Shoe + get 1 Socks free',
            'program_type': 'public_unique_code',
            'program_code': 'ODOO_AAAA',
            'purchase_type': 'product',
            'product_id': self.product_shoe.id,
            'product_quantity': 1,
            'reward_type': 'product',
            'reward_product_product_id': self.product_socks.id,
            'reward_quantity': 1,
            'state': 'opened',
        })

        self.couponprogram_7 = self.CouponProgram.create({
            'name': "GER Buy 1 laptop + get 10'%' off on cart",
            'program_type': 'generated_coupon',
            'purchase_type': 'product',
            'product_id': self.product_laptop.id,
            'product_quantity': 1,
            'reward_type': 'discount',
            'reward_discount_type': 'percentage',
            'reward_discount_on': 'cart',
            'reward_discount_percentage': 10,
            'state': 'opened',
        })

        self.couponprogram_8 = self.CouponProgram.create({
            'name': 'Buy 1 refrigerator + get shipment free',
            'program_type': 'apply_immediately',
            'purchase_type': 'product',
            'product_id': self.product_refrigerator.id,
            'product_quantity': 1,
            'reward_type': 'free_shipping',
            'state': 'opened',
        })

        self.couponprogram_9 = self.CouponProgram.create({
            'name': "Buy 1 iPhone + get coupon for 10'%' off the laptop",
            'program_type': 'apply_immediately',
            'purchase_type': 'product',
            'product_id': self.product_iphone.id,
            'product_quantity': 1,
            'reward_type': 'coupon',
            'reward_gift_program_id': self.couponprogram_7.id,
            'state': 'opened',
        })

# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from openerp import fields
from openerp.tests import common

class TestSaleCouponCommon(common.TransactionCase):

    def setUp(self):
        super(TestSaleCouponCommon, self).setUp()

        # Usefull models
        self.sale_coupon_type = self.env['sales.coupon.type']
        self.sale_coupon = self.env['sales.coupon']
        self.product = self.env['product.product']
        self.partner = self.env['res.partner']
        self.sale_order = self.env['sale.order']

        # create partner for sale order.
        self.partner_id = self.partner.create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
        })

        self.test_coupon_type1 = self.sale_coupon_type.create({
            'name': 'TestCoupon1',
            'validity_duration': 'month',
            'duration': 1,
            'expiration_use': 3,
        })

        # create product with coupon type
        self.conference_product = self.product.create({
            'name': 'National Conference',
            'type': 'service',
            'coupon_type': self.test_coupon_type1.id,
        })

        # create product 2 without coupon type
        self.training_product = self.product.create({
            'name': 'Training',
            'type': 'service',
        })

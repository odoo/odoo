# -*- coding: utf-8 -*-

from odoo.tests import common


class TestStockDropshippingCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestStockDropshippingCommon, cls).setUpClass()
        cls.payment_term = cls.env['account.payment.term'].create({
            'name': 'End of Following Month',
            'line_ids': [(0, 0, {
                'value': 'balance',
                'days': 31,
                'option': 'day_following_month',
            })],
        })
        cls.supplier = cls.env['res.partner'].create({'name': "Demo Supplier"})
        cls.customer = cls.env['res.partner'].create({'name': "Demo Customer"})

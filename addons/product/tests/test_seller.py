# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSeller(TransactionCase):

    def setUp(self):
        super(TestSeller, self).setUp()
        self.product_service = self.env.ref('product.product_product_2')
        self.product_service.default_code = 'DEFCODE'
        self.asustec = self.env.ref('base.res_partner_1')
        self.camptocamp = self.env.ref('base.res_partner_12')

    def test_10_sellers(self):
        self.product_service.write({'seller_ids': [
            (0, 0, {'name': self.asustec.id, 'product_code': 'ASUCODE'}),
            (0, 0, {'name': self.camptocamp.id, 'product_code': 'C2CCODE'}),
        ]})

        default_code = self.product_service.code
        self.assertEqual("DEFCODE", default_code, "Default code not used in product name")

        context_code = self.product_service\
                           .with_context(partner_id=self.camptocamp.id)\
                           .code
        self.assertEqual('C2CCODE', context_code, "Partner's code not used in product name with context set")

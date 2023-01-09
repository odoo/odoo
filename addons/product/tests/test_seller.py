# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase
from odoo.tools import float_compare


@tagged('post_install', '-at_install')
class TestSeller(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_service = cls.env['product.product'].create({
            'name': 'Virtual Home Staging',
        })
        cls.product_service.default_code = 'DEFCODE'
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Boudin',
            'type': 'consu',
        })
        cls.product_consu.default_code = 'DEFCODE'
        cls.asustec = cls.env['res.partner'].create({'name': 'Wood Corner'})
        cls.camptocamp = cls.env['res.partner'].create({'name': 'Azure Interior'})

    def test_10_sellers(self):
        self.product_service.write({'seller_ids': [
            (0, 0, {'partner_id': self.asustec.id, 'product_code': 'ASUCODE'}),
            (0, 0, {'partner_id': self.camptocamp.id, 'product_code': 'C2CCODE'}),
        ]})

        default_code = self.product_service.code
        self.assertEqual("DEFCODE", default_code, "Default code not used in product name")

        context_code = self.product_service\
                           .with_context(partner_id=self.camptocamp.id)\
                           .code
        self.assertEqual('C2CCODE', context_code, "Partner's code not used in product name with context set")

    def test_20_sellers_company(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({
            'name': 'Saucisson Inc.',
        })
        self.product_consu.write({'seller_ids': [
            (0, 0, {'partner_id': self.asustec.id, 'product_code': 'A', 'company_id': company_a.id}),
            (0, 0, {'partner_id': self.asustec.id, 'product_code': 'B', 'company_id': company_b.id}),
            (0, 0, {'partner_id': self.asustec.id, 'product_code': 'NO', 'company_id': False}),
        ]})

        names = self.product_consu.with_context(
            partner_id=self.asustec.id,
        ).name_get()
        ref = set([x[1] for x in names])
        self.assertEqual(len(names), 3, "3 vendor references should have been found")
        self.assertEqual(ref, {'[A] Boudin', '[B] Boudin', '[NO] Boudin'}, "Incorrect vendor reference list")
        names = self.product_consu.with_context(
            partner_id=self.asustec.id,
            company_id=company_a.id,
        ).name_get()
        ref = set([x[1] for x in names])
        self.assertEqual(len(names), 2, "2 vendor references should have been found")
        self.assertEqual(ref, {'[A] Boudin', '[NO] Boudin'}, "Incorrect vendor reference list")
        names = self.product_consu.with_context(
            partner_id=self.asustec.id,
            company_id=company_b.id,
        ).name_get()
        ref = set([x[1] for x in names])
        self.assertEqual(len(names), 2, "2 vendor references should have been found")
        self.assertEqual(ref, {'[B] Boudin', '[NO] Boudin'}, "Incorrect vendor reference list")

    def test_30_select_seller(self):
        self.res_partner_1 = self.asustec
        self.res_partner_4 = self.camptocamp
        self.ipad_mini, self.monitor = self.env['product.product'].create([{
            'name': 'Large Cabinet',
            'standard_price': 800.0,
        }, {
            'name': 'Super nice monitor',
            'list_price': 1000.0,
        }])

        self.env['product.supplierinfo'].create([
            {
                'partner_id': self.res_partner_1.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 750,
            }, {
                'partner_id': self.res_partner_4.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 790,
            }, {
                'partner_id': self.res_partner_4.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 3,
                'price': 785,
            }, {
                'partner_id': self.res_partner_4.id,
                'product_tmpl_id': self.monitor.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 3,
                'price': 100,
            }
        ])

        product = self.ipad_mini
        # Supplierinfo pricing

        # I check cost price of LCD Monitor.
        price = product._select_seller(partner_id=self.res_partner_4, quantity=1.0).price
        msg = "Wrong cost price: LCD Monitor. should be 790 instead of %s" % price
        self.assertEqual(float_compare(price, 790, precision_digits=2), 0, msg)

        # I check cost price of LCD Monitor if more than 3 Unit.
        price = product._select_seller(partner_id=self.res_partner_4, quantity=3.0).price
        msg = "Wrong cost price: LCD Monitor if more than 3 Unit.should be 785 instead of %s" % price
        self.assertEqual(float_compare(price, 785, precision_digits=2), 0, msg)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSeller(TransactionCase):

    def setUp(self):
        super(TestSeller, self).setUp()
        self.product_service = self.env['product.product'].create({
            'name': 'Virtual Home Staging',
        })
        self.product_service.default_code = 'DEFCODE'
        self.product_consu = self.env['product.product'].create({
            'name': 'Boudin',
            'type': 'consu',
        })
        self.product_consu.default_code = 'DEFCODE'
        self.asustec = self.env['res.partner'].create({'name': 'Wood Corner'})
        self.camptocamp = self.env['res.partner'].create({'name': 'Azure Interior'})

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

    def test_20_sellers_company(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({
            'name': 'Saucisson Inc.',
        })
        self.product_consu.write({'seller_ids': [
            (0, 0, {'name': self.asustec.id, 'product_code': 'A', 'company_id': company_a.id}),
            (0, 0, {'name': self.asustec.id, 'product_code': 'B', 'company_id': company_b.id}),
            (0, 0, {'name': self.asustec.id, 'product_code': 'NO', 'company_id': False}),
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

    def test_30_seller_ids(self):
        vendors = self.env['product.supplierinfo'].create([{
            'name': self.asustec.id,
            'product_tmpl_id': self.product_consu.product_tmpl_id.id,
        }, {
            'name': self.camptocamp.id,
            'product_id': self.product_consu.id,
        }])
        self.assertEqual(vendors, self.product_consu.seller_ids,
            "Sellers of a product should be listed in the product's seller_ids")
        vendors.write({'product_id': False})
        self.assertEqual(vendors, self.product_consu.seller_ids,
            "Setting the product_id to False shouldn't affect seller_ids.")

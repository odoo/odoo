# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestProductPricelistDemo(TransactionCase):

    def setUp(self):
        super(TestProductPricelistDemo, self).setUp()
        self.product_product_4 = self.env.ref('product.product_product_4')
        self.product_product_25 = self.env.ref('product.product_product_25')
        self.product_category_5 = self.env.ref('product.product_category_5')
        self.product_uom_unit = self.env.ref('product.product_uom_unit')
        self.list0 = self.env.ref('product.list0')

        self.product_pricelist = self.env['product.pricelist']

        self.product_product_4.write({'uom_id': self.product_uom_unit.id, 'categ_id': self.product_category_5.id})
        self.customer_pricelist = self.product_pricelist.create({
            'name': 'Customer Pricelist',
            'item_ids': [(0, 0, {
                'name': 'Default pricelist',
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': self.list0.id
            }), (0, 0, {
                'name': '10% Discount on Assemble Computer',
                'applied_on': '1_product',
                'sequence': 1,
                'product_id': self.product_product_4.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_discount': 10
            }), (0, 0, {
                'name': '1 surchange on Laptop',
                'applied_on': '1_product',
                'sequence': 1,
                'product_id': self.product_product_25.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_surcharge': 1
            }), (0, 0, {
                'name': '5% Discount on all Computer related products',
                'applied_on': '2_product_category',
                'sequence': 1,
                'min_quantity': 2,
                'compute_price': 'formula',
                'base': 'list_price',
                'categ_id': self.product_category_5.id,
                'price_discount': 5
            }), (0, 0, {
                'name': '30% Discount on all products',
                'applied_on': '0_product_variant',
                'date_start': '2011-12-27',
                'date_end': '2011-12-31',
                'compute_price': 'formula',
                'price_discount': 30,
                'sequence': 1,
                'base': 'list_price'
            })]
        })

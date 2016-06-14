# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestProductPricelistDemo(TransactionCase):

    def setUp(self):
        super(TestProductPricelistDemo, self).setUp()
        self.ProductPricelist = self.env['product.pricelist']
        self.res_partner_4 = self.env.ref('base.res_partner_4')
        self.computer_SC234 = self.env.ref("product.product_product_3")
        self.ipad_retina_display = self.env.ref('product.product_product_4')
        self.custom_computer_kit = self.env.ref("product.product_product_5")
        self.ipad_mini = self.env.ref("product.product_product_6")
        self.apple_in_ear_headphones = self.env.ref("product.product_product_7")
        self.laptop_E5023 = self.env.ref('product.product_delivery_01')
        self.laptop_S3450 = self.env.ref("product.product_product_25")
        self.category_5_id = self.ref('product.product_category_5')
        self.uom_unit_id = self.ref('product.product_uom_unit')
        self.list0 = self.ref('product.list0')

        self.ipad_retina_display.write({'uom_id': self.uom_unit_id, 'categ_id': self.category_5_id})
        self.customer_pricelist = self.ProductPricelist.create({
            'name': 'Customer Pricelist',
            'item_ids': [(0, 0, {
                'name': 'Default pricelist',
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': self.list0
            }), (0, 0, {
                'name': '10% Discount on Assemble Computer',
                'applied_on': '1_product',
                'sequence': 1,
                'product_id': self.ipad_retina_display.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_discount': 10
            }), (0, 0, {
                'name': '1 surchange on Laptop',
                'applied_on': '1_product',
                'sequence': 4,
                'product_id': self.laptop_E5023.id,
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
                'categ_id': self.category_5_id,
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

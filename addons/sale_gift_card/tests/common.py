# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


class TestSaleGiftCardCommon(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # set currency to not rely on demo data and avoid possible race condition
        cls.currency_ratio = 1.0
        pricelist = cls.env.ref("product.list0")
        pricelist.currency_id = cls._setup_currency(cls.currency_ratio)


        # create partner for sale order.
        cls.fatima = cls.env['res.partner'].create({
            'name': 'Fatima Kalai',
            'email': 'fatima.kalai@example.com',
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.fatima.id
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Taxes
        cls.tax_15pc_excl = cls.env['account.tax'].create({
            'name': "Tax 15%",
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
        })

        #products
        cls.product_A = cls.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_15pc_excl.id])],
        })
        cls.product_gift_card = cls.env['product.product'].create({
            'name': 'Gift Card 50',
            'detailed_type': 'gift',
            'list_price': 50,
            'sale_ok': True,
            'taxes_id': False,
        })

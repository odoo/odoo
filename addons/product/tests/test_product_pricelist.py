# -*- coding: utf-8 -*-

from openerp.addons.product.tests.test_product_pricelist_demo import TestProductPricelistDemo
from openerp.tools import float_compare
from openerp.tools import test_reports

class TestProductPricelist(TestProductPricelistDemo):

    def test_10_calculation_price_of_products_pricelist(self):

        product_6 = self.env.ref("product.product_product_6")

        """I check sale price of Assemble Computer"""
        context = {}
        context.update({'pricelist': self.customer_pricelist.id, 'quantity': 1})
        product_4 = self.product_product_4.with_context(context)
        self.assertEqual(float_compare(product_4.price, (product_4.lst_price-product_4.lst_price*(0.10)), precision_digits=2), 0, "Wrong sale price: Assemble Computer.")

        """I check sale price of Laptop."""
        product_25 = self.product_product_25.with_context(context)
        self.assertEqual(float_compare(product_25.price, product_25.lst_price + 1, precision_digits=2), 0, "Wrong sale price: Laptop.")

        """I check sale price of IT component."""
        product = self.env.ref("product.product_product_7")
        product_7 = product.with_context(context)
        self.assertEqual(float_compare(product_7.price, product_7.lst_price, precision_digits=2), 0, "Wrong sale price: IT component.")

        """I check sale price of IT component if more than 3 Unit."""
        context.update({'quantity': 5})
        product = self.env.ref("product.product_product_26")
        product_26 = product.with_context(context)
        self.assertEqual(float_compare(product_26.price, product_26.lst_price-product_26.lst_price*(0.05), precision_digits=2), 0, "Wrong sale price: IT component if more than 3 Unit.")

        """I check sale price of LCD Monitor."""
        context.update({'quantity': 1})
        product_6 = product_6.with_context(context)
        self.assertEqual(float_compare(product_6.price, product_6.lst_price, precision_digits=2), 0, "Wrong sale price: LCD Monitor.")

        """I check sale price of LCD Monitor on end of year."""
        context.update({'quantity': 1, 'date': '2011-12-31'})
        product_6 = product_6.with_context(context)
        self.assertEqual(float_compare(product_6.price, product_6.lst_price-product_6.lst_price*(0.30), precision_digits=2), 0, "Wrong sale price: LCD Monitor on end of year.")

        """I check cost price of LCD Monitor."""
        context.update({'quantity': 1, 'date': False, 'partner_id': self.env.ref('base.res_partner_4').id})
        product_6 = product_6.with_context(context)
        self.assertEqual(float_compare(product_6.seller_price, 790, precision_digits=2), 0, "Wrong cost price: LCD Monitor.")

        """I check cost price of LCD Monitor if more than 3 Unit."""
        context.update({'quantity': 3})
        product_6 = product_6.with_context(context)
        self.assertEqual(float_compare(product_6.seller_price, 785, precision_digits=2), 0, "Wrong cost price: LCD Monitor if more than 3 Unit.")

        """I print the sale prices report."""
        ctx = {'active_model': 'product.product', 'date': '2011-12-30', 'active_ids': [self.env.ref('product.product_product_3').id, self.env.ref('product.product_product_4').id, self.env.ref('product.product_product_5').id, self.env.ref('product.product_product_6').id]}
        data_dict = {
            'qty1': 1,
            'qty2': 5,
            'qty3': 10,
            'qty4': 15,
            'qty5': 30,
            'price_list': self.customer_pricelist.id,
        }
        test_reports.try_report_action(self.cr, self.uid, 'action_product_price_list', wiz_data=data_dict, context=ctx, our_module='product')

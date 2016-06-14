# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.product.tests.test_product_pricelist_demo import TestProductPricelistDemo
from odoo.tools import float_compare, test_reports


class TestProductPricelist(TestProductPricelistDemo):

    def test_10_calculation_price_of_products_pricelist(self):
        """Test calculation of product price based on pricelist"""
        # I check sale price of iPad Retina Display
        context = {}
        context.update({'pricelist': self.customer_pricelist.id, 'quantity': 1})
        ipad_retina_display = self.ipad_retina_display.with_context(context)
        msg = "Wrong sale price: iPad Retina Display. should be %s instead of %s" % (ipad_retina_display.price, (ipad_retina_display.lst_price-ipad_retina_display.lst_price*(0.10)))
        self.assertEqual(float_compare(ipad_retina_display.price, (ipad_retina_display.lst_price-ipad_retina_display.lst_price*(0.10)), precision_digits=2), 0, msg)

        # I check sale price of Laptop.
        laptop_E5023 = self.laptop_E5023.with_context(context)
        msg = "Wrong sale price: Laptop. should be %s instead of %s" % (laptop_E5023.price, (laptop_E5023.lst_price + 1))
        self.assertEqual(float_compare(laptop_E5023.price, laptop_E5023.lst_price + 1, precision_digits=2), 0, msg)

        # I check sale price of IT component.
        apple_headphones = self.apple_in_ear_headphones.with_context(context)
        msg = "Wrong sale price: IT component. should be %s instead of %s" % (apple_headphones.price, apple_headphones.lst_price)
        self.assertEqual(float_compare(apple_headphones.price, apple_headphones.lst_price, precision_digits=2), 0, msg)

        # I check sale price of IT component if more than 3 Unit.
        context.update({'quantity': 5})
        laptop_S3450 = self.laptop_S3450.with_context(context)
        msg = "Wrong sale price: IT component if more than 3 Unit. should be %s instead of %s" % (laptop_S3450.price, (laptop_S3450.lst_price-laptop_S3450.lst_price*(0.05)))
        self.assertEqual(float_compare(laptop_S3450.price, laptop_S3450.lst_price-laptop_S3450.lst_price*(0.05), precision_digits=2), 0, msg)

        # I check sale price of LCD Monitor.
        context.update({'quantity': 1})
        ipad_mini = self.ipad_mini.with_context(context)
        msg = "Wrong sale price: LCD Monitor. should be %s instead of %s" % (ipad_mini.price, ipad_mini.lst_price)
        self.assertEqual(float_compare(ipad_mini.price, ipad_mini.lst_price, precision_digits=2), 0, msg)

        # I check sale price of LCD Monitor on end of year.
        context.update({'quantity': 1, 'date': '2011-12-31'})
        ipad_mini = self.ipad_mini.with_context(context)
        msg = "Wrong sale price: LCD Monitor on end of year. should be %s instead of %s" % (ipad_mini.price, ipad_mini.lst_price-ipad_mini.lst_price*(0.30))
        self.assertEqual(float_compare(ipad_mini.price, ipad_mini.lst_price-ipad_mini.lst_price*(0.30), precision_digits=2), 0, msg)

        # I check cost price of LCD Monitor.
        context.update({'quantity': 1, 'date': False, 'partner_id': self.res_partner_4.id})
        ipad_mini = self.ipad_mini.with_context(context)
        partner = self.res_partner_4.with_context(context)
        msg = "Wrong cost price: LCD Monitor. should be 790 instead of %s" % ipad_mini._select_seller(partner_id=partner, quantity=1.0).price
        self.assertEqual(float_compare(ipad_mini._select_seller(partner_id=partner, quantity=1.0).price, 790, precision_digits=2), 0, msg)

        # I check cost price of LCD Monitor if more than 3 Unit.
        context.update({'quantity': 3})
        ipad_mini = self.ipad_mini.with_context(context)
        partner = self.res_partner_4.with_context(context)
        msg = "Wrong cost price: LCD Monitor if more than 3 Unit.should be 785 instead of %s" % ipad_mini._select_seller(partner_id=partner, quantity=3.0).price
        self.assertEqual(float_compare(ipad_mini._select_seller(partner_id=partner, quantity=3.0).price, 785, precision_digits=2), 0, msg)

        # I print the sale prices report.
        ctx = {'active_model': 'product.product', 'date': '2011-12-30', 'active_ids': [self.computer_SC234.id, self.ipad_retina_display.id, self.custom_computer_kit.id, self.ipad_mini.id]}
        data_dict = {
            'qty1': 1,
            'qty2': 5,
            'qty3': 10,
            'qty4': 15,
            'qty5': 30,
            'price_list': self.customer_pricelist.id,
        }
        test_reports.try_report_action(self.cr, self.uid, 'action_product_price_list', wiz_data=data_dict, context=ctx, our_module='product')

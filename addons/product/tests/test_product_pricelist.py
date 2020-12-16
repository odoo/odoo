# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase
from odoo.tools import float_compare, test_reports


class TestProductPricelist(TransactionCase):

    def setUp(self):
        super(TestProductPricelist, self).setUp()
        self.ProductPricelist = self.env['product.pricelist']
        self.res_partner_4 = self.env['res.partner'].create({'name': 'Ready Mat'})
        self.res_partner_1 = self.env['res.partner'].create({'name': 'Wood Corner'})
        self.category_5_id = self.env['product.category'].create({
            'name': 'Office Furniture',
            'parent_id': self.env.ref('product.product_category_1').id
        }).id
        self.computer_SC234 = self.env['product.product'].create({
            'name': 'Desk Combination',
            'categ_id': self.category_5_id,
        })
        self.ipad_retina_display = self.env['product.product'].create({
            'name': 'Customizable Desk',
        })
        self.custom_computer_kit = self.env['product.product'].create({
            'name': 'Corner Desk Right Sit',
            'categ_id': self.category_5_id,
        })
        self.ipad_mini = self.env['product.product'].create({
            'name': 'Large Cabinet',
            'categ_id': self.category_5_id,
            'standard_price': 800.0,
        })
        self.monitor = self.env['product.product'].create({
            'name': 'Super nice monitor',
            'categ_id': self.category_5_id,
            'list_price': 1000.0,
        })

        self.env['product.supplierinfo'].create([
            {
                'name': self.res_partner_1.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 750,
            }, {
                'name': self.res_partner_4.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 790,
            }, {
                'name': self.res_partner_4.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 3,
                'price': 785,
            }, {
                'name': self.res_partner_4.id,
                'product_tmpl_id': self.monitor.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 3,
                'price': 100,
            }
        ])
        self.apple_in_ear_headphones = self.env['product.product'].create({
            'name': 'Storage Box',
            'categ_id': self.category_5_id,
        })
        self.laptop_E5023 = self.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': self.category_5_id,
        })
        self.laptop_S3450 = self.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'categ_id': self.category_5_id,
        })

        self.uom_unit_id = self.ref('uom.product_uom_unit')
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
                'product_tmpl_id': self.ipad_retina_display.product_tmpl_id.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_discount': 10
            }), (0, 0, {
                'name': '1 surchange on Laptop',
                'applied_on': '1_product',
                'product_tmpl_id': self.laptop_E5023.product_tmpl_id.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_surcharge': 1
            }), (0, 0, {
                'name': '5% Discount on all Computer related products',
                'applied_on': '2_product_category',
                'min_quantity': 2,
                'compute_price': 'formula',
                'base': 'list_price',
                'categ_id': self.category_5_id,
                'price_discount': 5
            }), (0, 0, {
                'name': '30% Discount on all products',
                'applied_on': '3_global',
                'date_start': '2011-12-27',
                'date_end': '2011-12-31',
                'compute_price': 'formula',
                'price_discount': 30,
                'base': 'list_price'
            }), (0, 0, {
                 'name': 'Fixed on all products',
                 'applied_on': '1_product',
                 'product_tmpl_id': self.monitor.product_tmpl_id.id,
                 'date_start': '2020-04-06 09:00:00',
                 'date_end': '2020-04-09 12:00:00',
                 'compute_price': 'formula',
                 'price_discount': 50,
                 'base': 'list_price'
             })]
        })

    def test_10_calculation_price_of_products_pricelist(self):
        """Test calculation of product price based on pricelist"""
        # I check sale price of Customizable Desk
        context = {}
        context.update({'pricelist': self.customer_pricelist.id, 'quantity': 1})
        ipad_retina_display = self.ipad_retina_display.with_context(context)
        msg = "Wrong sale price: Customizable Desk. should be %s instead of %s" % (ipad_retina_display.price, (ipad_retina_display.lst_price-ipad_retina_display.lst_price*(0.10)))
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

        # Check if the pricelist is applied at precise datetime
        context.update({'quantity': 1, 'date': datetime.strptime('2020-04-05 08:00:00', '%Y-%m-%d %H:%M:%S')})
        monitor = self.monitor.with_context(context)
        partner = self.res_partner_4.with_context(context)
        msg = "Wrong cost price: LCD Monitor. should be 1000 instead of %s" % monitor._select_seller(
            partner_id=partner, quantity=1.0).price
        self.assertEqual(
            float_compare(monitor.price, monitor.lst_price, precision_digits=2), 0,
            msg)
        context.update({'quantity': 1, 'date': datetime.strptime('2020-04-06 10:00:00', '%Y-%m-%d %H:%M:%S')})
        monitor = self.monitor.with_context(context)
        msg = "Wrong cost price: LCD Monitor. should be 500 instead of %s" % monitor._select_seller(
            partner_id=partner, quantity=1.0).price
        self.assertEqual(
            float_compare(monitor.price, monitor.lst_price/2, precision_digits=2), 0,
            msg)



# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import time

from odoo.fields import Command, first
from odoo.tools import float_compare

from odoo.addons.product.tests.common import ProductCommon


class TestProductPricelist(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.category_5_id = cls.env['product.category'].create({
            'name': 'Office Furniture',
            'parent_id': cls.product_category.id
        }).id
        cls.computer_SC234 = cls.env['product.product'].create({
            'name': 'Desk Combination',
            'categ_id': cls.category_5_id,
        })
        cls.ipad_retina_display = cls.env['product.product'].create({
            'name': 'Customizable Desk',
        })
        cls.custom_computer_kit = cls.env['product.product'].create({
            'name': 'Corner Desk Right Sit',
            'categ_id': cls.category_5_id,
        })
        cls.ipad_mini = cls.env['product.product'].create({
            'name': 'Large Cabinet',
            'categ_id': cls.category_5_id,
            'standard_price': 800.0,
        })
        cls.monitor = cls.env['product.product'].create({
            'name': 'Super nice monitor',
            'categ_id': cls.category_5_id,
            'list_price': 1000.0,
        })

        cls.apple_in_ear_headphones = cls.env['product.product'].create({
            'name': 'Storage Box',
            'categ_id': cls.category_5_id,
        })
        cls.laptop_E5023 = cls.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': cls.category_5_id,
        })
        cls.laptop_S3450 = cls.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'categ_id': cls.category_5_id,
        })
        cls.product_multi_price = cls.env['product.product'].create({
            'name': 'Multi Price',
            'categ_id': cls.product_category.id,
        })

        cls.new_currency = cls.env['res.currency'].create({
            'name': 'Wonderful Currency',
            'symbol': ':)',
            'rate_ids': [Command.create({'rate': 10, 'name': time.strftime('%Y-%m-%d')})],
        })

        cls.ipad_retina_display.write({'uom_id': cls.uom_unit.id, 'categ_id': cls.category_5_id})
        cls.customer_pricelist = cls.env['product.pricelist'].create({
            'name': 'Customer Pricelist',
            'item_ids': [
                Command.create({
                    'name': 'Default pricelist',
                    'compute_price': 'formula',
                    'base': 'pricelist',
                    'base_pricelist_id': cls.pricelist.id,
                }),
                Command.create({
                    'name': '10% Discount on Assemble Computer',
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.ipad_retina_display.product_tmpl_id.id,
                    'compute_price': 'formula',
                    'base': 'list_price',
                    'price_discount': 10,
                }),
                Command.create({
                    'name': '1 surchange on Laptop',
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.laptop_E5023.product_tmpl_id.id,
                    'compute_price': 'formula',
                    'base': 'list_price',
                    'price_surcharge': 1,
                }),
                Command.create({
                    'name': '5% Discount on all Computer related products',
                    'applied_on': '2_product_category',
                    'min_quantity': 2,
                    'compute_price': 'formula',
                    'base': 'list_price',
                    'categ_id': cls.product_category.id,
                    'price_discount': 5,
                }),
                Command.create({
                    'name': '30% Discount on all products',
                    'applied_on': '3_global',
                    'date_start': '2011-12-27',
                    'date_end': '2011-12-31',
                    'compute_price': 'formula',
                    'price_discount': 30,
                    'base': 'list_price',
                }),
                Command.create({
                    'name': 'Fixed on all products',
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.monitor.product_tmpl_id.id,
                    'date_start': '2020-04-06 09:00:00',
                    'date_end': '2020-04-09 12:00:00',
                    'compute_price': 'formula',
                    'price_discount': 50,
                    'base': 'list_price',
                }),
                Command.create({
                    'name': 'Multi Price Customer',
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.product_multi_price.product_tmpl_id.id,
                    'compute_price': 'fixed',
                    'fixed_price': 99,
                    'base': 'list_price',
                }),
            ],
        })
        cls.business_pricelist = cls.env['product.pricelist'].create({
            'name': 'Business Pricelist',
            'item_ids': [(0, 0, {
                 'name': 'Multi Price Business',
                 'applied_on': '1_product',
                 'product_tmpl_id': cls.product_multi_price.product_tmpl_id.id,
                 'compute_price': 'fixed',
                 'fixed_price': 50,
                 'base': 'list_price'
             })]
        })

    def test_10_calculation_price_of_products_pricelist(self):
        """Test calculation of product price based on pricelist"""
        # I check sale price of Customizable Desk
        context = {}
        context.update({'pricelist': self.customer_pricelist.id, 'quantity': 1})
        product = self.ipad_retina_display
        price = self.customer_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong sale price: Customizable Desk. should be %s instead of %s" % (price, (product.lst_price-product.lst_price*(0.10)))
        self.assertEqual(float_compare(
            price, (product.lst_price-product.lst_price*(0.10)), precision_digits=2), 0, msg)

        # I check sale price of Laptop.
        product = self.laptop_E5023
        price = self.customer_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong sale price: Laptop. should be %s instead of %s" % (price, (product.lst_price + 1))
        self.assertEqual(float_compare(price, product.lst_price + 1, precision_digits=2), 0, msg)

        # I check sale price of IT component.
        product = self.apple_in_ear_headphones
        price = self.customer_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong sale price: IT component. should be %s instead of %s" % (price, product.lst_price)
        self.assertEqual(float_compare(price, product.lst_price, precision_digits=2), 0, msg)

        # I check sale price of IT component if more than 3 Unit.
        context.update({'quantity': 5})
        product = self.laptop_S3450
        price = self.customer_pricelist._get_product_price(product, quantity=5.0)
        msg = "Wrong sale price: IT component if more than 3 Unit. should be %s instead of %s" % (price, (product.lst_price-product.lst_price*(0.05)))
        self.assertEqual(float_compare(price, product.lst_price-product.lst_price*(0.05), precision_digits=2), 0, msg)

        # I check sale price of LCD Monitor.
        product = self.ipad_mini
        price = self.customer_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong sale price: LCD Monitor. should be %s instead of %s" % (price, product.lst_price)
        self.assertEqual(float_compare(price, product.lst_price, precision_digits=2), 0, msg)

        # I check sale price of LCD Monitor on end of year.
        price = self.customer_pricelist._get_product_price(product, quantity=1.0, date='2011-12-31')
        msg = "Wrong sale price: LCD Monitor on end of year. should be %s instead of %s" % (price, product.lst_price-product.lst_price*(0.30))
        self.assertEqual(float_compare(price, product.lst_price-product.lst_price*(0.30), precision_digits=2), 0, msg)

        # Check if the pricelist is applied at precise datetime
        product = self.monitor
        price = self.customer_pricelist._get_product_price(product, quantity=1.0, date='2020-04-05 08:00:00')
        context.update({'quantity': 1, 'date': datetime.strptime('2020-04-05 08:00:00', '%Y-%m-%d %H:%M:%S')})
        msg = "Wrong cost price: LCD Monitor. should be 1000 instead of %s" % price
        self.assertEqual(
            float_compare(price, product.lst_price, precision_digits=2), 0,
            msg)
        price = self.customer_pricelist._get_product_price(product, quantity=1.0, date='2020-04-06 10:00:00')
        msg = "Wrong cost price: LCD Monitor. should be 500 instead of %s" % price
        self.assertEqual(
            float_compare(price, product.lst_price/2, precision_digits=2), 0,
            msg)

        # Check if the price is different when we change the pricelist
        product = self.product_multi_price
        price = self.customer_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong price: Multi Product Price. should be 99 instead of %s" % price
        self.assertEqual(float_compare(price, 99, precision_digits=2), 0, msg)

        price = self.business_pricelist._get_product_price(product, quantity=1.0)
        msg = "Wrong price: Multi Product Price. should be 50 instead of %s" % price
        self.assertEqual(float_compare(price, 50, precision_digits=2), 0, msg)

    def test_20_price_different_currency_pricelist(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Currency Pricelist',
            'currency_id': self.new_currency.id,
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'list_price',
                'price_surcharge': 100
            })]
        })
        price = pricelist._get_product_price(self.monitor, quantity=1.0)
        # product price use the currency of the pricelist
        self.assertEqual(price, 10100)

    def test_21_price_diff_cur_min_margin_pricelist(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Currency with Margin Pricelist',
            'currency_id': self.new_currency.id,
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'list_price',
                'price_min_margin': 10,
                'price_max_margin': 100,
            })]
        })
        price = pricelist._get_product_price(self.monitor, quantity=1.0)
        # product price use the currency of the pricelist
        self.assertEqual(price, 10010)

    def test_22_price_diff_cur_max_margin_pricelist(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Currency with Margin Pricelist',
            'currency_id': self.new_currency.id,
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'list_price',
                'price_surcharge': 100,
                'price_max_margin': 90
            })]
        })
        price = pricelist._get_product_price(self.monitor, quantity=1.0)
        # product price use the currency of the pricelist
        self.assertEqual(price, 10090)

    def test_price_without_pricelist_fallback_product_price(self):
        ProductPricelist = self.env['product.pricelist']
        spam = self.env['product.product'].create({
            'name': '1 tonne of spam',
            'uom_id': self.uom_ton.id,
            'uom_po_id': self.uom_ton.id,
            'list_price': 100,
            'type': 'consu'
        })
        self.assertEqual(
            ProductPricelist._get_product_price(self.monitor, quantity=1.0),
            self.monitor.list_price,
            msg="without pricelist, the price should be the same as the list price",
        )
        self.assertEqual(
            ProductPricelist._get_product_price(self.monitor, quantity=1.0, currency=self.new_currency),
            self.monitor.list_price*10,
            msg="without pricelist but with a currency different than the product one, the price "
                "should be the same as the list price converted with the currency rate",
        )
        self.assertEqual(
            ProductPricelist._get_product_price(spam, quantity=1.0, uom=self.uom_kgm),
            spam.list_price / 1000,
            msg="the product price should be converted using the specified uom",
        )
        self.assertEqual(
            ProductPricelist._get_product_price(
                spam, quantity=1.0, currency=self.new_currency, uom=self.uom_kgm
            ),
            spam.list_price / 100,
            msg="the product price should be converted using the specified uom and converted to the"
                " correct currency",
        )

    def test_30_pricelist_delete(self):
        """ Test that `unlink` on many records doesn't raise a RecursionError. """
        self.customer_pricelist = self.env['product.pricelist'].create({
            'name': 'Customer Pricelist',
            'item_ids': [
                Command.create({
                    'compute_price': 'formula',
                }),
            ] * 101,
        })
        self.customer_pricelist.unlink()

    def test_40_pricelist_item_min_quantity_precision(self):
        """Test that the min_quantity has the precision of Product UoM."""
        # Arrange: Change precision digits
        uom_precision = self.env.ref("product.decimal_product_uom")
        uom_precision.digits = 3
        pricelist_item = first(self.customer_pricelist.item_ids[0])
        precise_value = 1.234

        # Act: Set a value for the increased precision
        pricelist_item.min_quantity = precise_value

        # Assert: The set value is kept
        self.assertEqual(pricelist_item.min_quantity, precise_value)

    def test_pricelist_sync_on_partners(self):
        ResPartner = self.env['res.partner']

        company_1, company_2 = self.env['res.company'].create([
            {'name': 'company_1'},
            {'name': 'company_2'},
        ])

        test_partner_company = ResPartner.create({
            'name': 'This company',
            'is_company': True,
        })
        test_partner_company.with_company(company_1).property_product_pricelist = self.business_pricelist.id
        test_partner_company.with_company(company_2).property_product_pricelist = self.customer_pricelist.id

        child_address = ResPartner.create({
            'name': 'Contact',
            'parent_id': test_partner_company.id,
        })
        self.assertEqual(
            child_address.property_product_pricelist,
            test_partner_company.property_product_pricelist,
        )
        self.assertEqual(
            child_address.with_company(company_1).property_product_pricelist,
            self.business_pricelist,
        )
        self.assertEqual(
            child_address.with_company(company_2).property_product_pricelist,
            self.customer_pricelist,
        )

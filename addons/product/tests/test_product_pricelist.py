# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from odoo.tools import float_compare, test_reports


class TestProductPricelist(common.TestPricelistCommon):

    def test_10_pricelist_discount(self):
        # Make sure the price using a pricelist is the same than without after
        # applying the computation manually

        usb_adapter = self.product_5
        datacard = self.product_6

        sale_pricelist = self.env['product.pricelist'].create({
            'name': 'Sale pricelist',
            'item_ids': [(0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_discount': 10,
                    'product_id': usb_adapter.id,
                    'applied_on': '0_product_variant',
                }), (0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_surcharge': -0.5,
                    'product_id': datacard.id,
                    'applied_on': '0_product_variant',
                })]
        })

        context = {}

        public_context = dict(context, pricelist_id=self.public_pricelist.id)
        pricelist_context = dict(context, pricelist_id=sale_pricelist.id)

        usb_adapter_without_pricelist = usb_adapter.with_context(public_context)
        usb_adapter_with_pricelist = usb_adapter.with_context(pricelist_context)
        self.assertEqual(usb_adapter_with_pricelist.lst_price, usb_adapter_with_pricelist.lst_price)
        self.assertEqual(usb_adapter_without_pricelist.lst_price, usb_adapter_without_pricelist.price)
        self.assertEqual(usb_adapter_with_pricelist.price, usb_adapter_without_pricelist.price*0.9)
        # VFE TODO ensure pricelist.get_product_price returns the same values as product.price

        datacard_without_pricelist = datacard.with_context(public_context)
        datacard_with_pricelist = datacard.with_context(pricelist_context)
        self.assertEqual(datacard_with_pricelist.price, datacard_without_pricelist.price-0.5)

        # Make sure that changing the unit of measure does not break the unit
        # price (after converting)
        unit_context = dict(context, pricelist_id=sale_pricelist.id, uom_id=self.uom_unit.id)
        dozen_context = dict(context, pricelist_id=sale_pricelist.id, uom_id=self.uom_dozen.id)

        usb_adapter_unit = usb_adapter.with_context(unit_context)
        usb_adapter_dozen = usb_adapter.with_context(dozen_context)
        self.assertAlmostEqual(usb_adapter_unit.price*12, usb_adapter_dozen.price)
        datacard_unit = datacard.with_context(unit_context)
        datacard_dozen = datacard.with_context(dozen_context)
        # price_surcharge applies to product default UoM, here "Units", so surcharge will be multiplied
        self.assertAlmostEqual(datacard_unit.price*12, datacard_dozen.price)

    def test_10_calculation_price_of_products_pricelist(self):
        """Test calculation of product price based on pricelist"""

        self.category_5 = self.env['product.category'].create({
            'name': 'Office Furniture',
            'parent_id': self.env.ref('product.product_category_1').id
        })
        # VFE TODO reuse products from product common ?
        self.computer_SC234 = self.env['product.product'].create({
            'name': 'Desk Combination',
            'categ_id': self.category_5.id,
        })
        self.ipad_retina_display = self.env['product.product'].create({
            'name': 'Customizable Desk',
        })
        self.custom_computer_kit = self.env['product.product'].create({
            'name': 'Corner Desk Right Sit',
            'categ_id': self.category_5.id,
        })
        self.ipad_mini = self.env['product.product'].create({
            'name': 'Large Cabinet',
            'categ_id': self.category_5.id,
            'standard_price': 800.0,
        })
        self.env['product.supplierinfo'].create([
            {
                'name': self.partner_3.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 750,
            }, {
                'name': self.partner_2.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 1,
                'price': 790,
            }, {
                'name': self.partner_2.id,
                'product_tmpl_id': self.ipad_mini.product_tmpl_id.id,
                'delay': 3,
                'min_qty': 3,
                'price': 785,
            }
        ])
        self.apple_in_ear_headphones = self.env['product.product'].create({
            'name': 'Storage Box',
            'categ_id': self.category_5.id,
        })
        self.laptop_E5023 = self.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': self.category_5.id,
        })
        self.laptop_S3450 = self.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'categ_id': self.category_5.id,
        })

        self.uom_unit_id = self.ref('uom.product_uom_unit')

        self.ipad_retina_display.write({'uom_id': self.uom_unit_id, 'categ_id': self.category_5.id})
        self.customer_pricelist = self.env['product.pricelist'].create({
            'name': 'Customer Pricelist',
            'item_ids': [(0, 0, {
                #  'name': '10% Discount on Assemble Computer',
                'applied_on': '1_product',
                'product_tmpl_id': self.ipad_retina_display.product_tmpl_id.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_discount': 10
            }), (0, 0, {
                #  'name': '1 surcharge on Laptop',
                'applied_on': '1_product',
                'product_tmpl_id': self.laptop_E5023.product_tmpl_id.id,
                'compute_price': 'formula',
                'base': 'list_price',
                'price_surcharge': 1
            }), (0, 0, {
                #  'name': '5% Discount on all Computer related products',
                'applied_on': '2_product_category',
                'min_quantity': 2,
                'compute_price': 'formula',
                'base': 'list_price',
                'categ_id': self.category_5.id,
                'price_discount': 5
            }), (0, 0, {
                #  'name': '30% Christmas Discount on all products',
                'applied_on': '3_global',
                'date_start': '2011-12-27',
                'date_end': '2011-12-31',
                'compute_price': 'formula',
                'price_discount': 30,
                'base': 'list_price'
            })]
        })

        # I check sale price of Customizable Desk
        context = {}
        context.update({'pricelist_id': self.customer_pricelist.id, 'quantity': 1})
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
        context.update({'quantity': 1, 'date': False, 'partner_id': self.partner_2.id})
        ipad_mini = self.ipad_mini.with_context(context)
        partner = self.partner_2.with_context(context)
        msg = "Wrong cost price: LCD Monitor. should be 790 instead of %s" % ipad_mini._select_seller(partner_id=partner, quantity=1.0).price
        self.assertEqual(float_compare(ipad_mini._select_seller(partner_id=partner, quantity=1.0).price, 790, precision_digits=2), 0, msg)

        # I check cost price of LCD Monitor if more than 3 Unit.
        context.update({'quantity': 3})
        ipad_mini = self.ipad_mini.with_context(context)
        partner = self.partner_2.with_context(context)
        msg = "Wrong cost price: LCD Monitor if more than 3 Unit.should be 785 instead of %s" % ipad_mini._select_seller(partner_id=partner, quantity=3.0).price
        self.assertEqual(float_compare(ipad_mini._select_seller(partner_id=partner, quantity=3.0).price, 785, precision_digits=2), 0, msg)

    def test_20_pricelist_multi_uom(self):
        # Verify that the pricelist rules are correctly using the product's default UoM
        # as reference, and return a result according to the target UoM.
        tonne_price = 100

        # make sure 'tonne' resolves down to 1 'kg'.
        self.uom_ton.rounding = 0.001

        # setup product stored in 'tonnes', with a discounted pricelist for qty > 3 tonnes
        spam = self.env['product.product'].create({
            'name': '1 tonne of spam',
            'uom_id': self.uom_ton.id,
            'uom_po_id': self.uom_ton.id,
            'list_price': tonne_price,
            'type': 'consu'
        })

        pricelist = self.public_pricelist

        self.env['product.pricelist.item'].create({
            'pricelist_id': pricelist.id,
            'applied_on': '0_product_variant',
            'compute_price': 'formula',
            'base': 'list_price',  # based on public price
            'min_quantity': 3,  # min = 3 tonnes
            'price_surcharge': -10,  # -10 EUR / tonne
            'product_id': spam.id
        })

        def test_unit_price(qty, uom, expected_unit_price):
            unit_price = pricelist.get_product_price(spam, qty, uom)
            self.assertAlmostEqual(unit_price, expected_unit_price, msg='Computed unit price is wrong')

        # Test prices - they are *per unit*, the quantity is only here to match the pricelist rules!
        test_unit_price(2, self.uom_kgm, tonne_price / 1000.0)
        test_unit_price(2000, self.uom_kgm, tonne_price / 1000.0)
        test_unit_price(3500, self.uom_kgm, (tonne_price - 10) / 1000.0)
        test_unit_price(2, self.uom_ton, tonne_price)
        test_unit_price(3, self.uom_ton, tonne_price - 10)

    def test_30_pricelist_multi_currency(self):
        # Product currency = product.company.currency / self.env.company.currency on creation
        # cost_currenty = self.env.company.currency
        # Test with pricelist in different currencies, based on standard_price/list_price
        # And verifies currency rates are correctly applied
        return

    def test_40_pricelist_multi_company(self):
        # Test currency changes on company
        # Verify check_company avoids basing a pricelist on a pricelist from another company
        # Ensure partner.property_product_pricelist is correctly recomputed on company change (with_company)
        return

    def test_50_advanced_pricelist(self):
        # Test pricelist formulas
        # product_category = self.env['product.category'].create({'name': "Specifics"})
        # advanced_pricelist = self.env['product.pricelist'].create({
        #     "name": "Advanced Test Pricelist",
        #     "currency_id": self.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global",
        #         "base": "list_price",
        #         "compute_price": "percentage",
        #         "percent_price": 55.0,
        #     }), (0, 0, {
        #         "applied_on": "2_product_category",
        #         "categ_id": product_category.id,
        #         "base": "list_price/standard_price/pricelist",
        #         "compute_price": "formula",
        #         "price_round": 100,
        #         "price_surcharge": 50,
        #         "price_discount": 55.0,
        #         "price_min_margin": 10.0,
        #         "price_max_margin": 500.0,
        #     })]
        # })
        return
        # cls.advanced_pricelist = cls.env['product.pricelist'].create({
        #     "name": "Advanced Test",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "list_price/standard_price/pricelist",
        #         "compute_price": "percentage/formula",
        #     })]
        # })

    def test_60_chained_pricelists(self):
        return
        # VFE TODO multiple currencies in the chain
        # VFE TODO multiple items in each pricelist.
        # VFE TODO multiple compute_price logic ? with a sales price, standard_price or fixed price in the end of the chain ?
        # cls.pricelist_chain_3 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - End",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "list_price/standard_price/pricelist",
        #         "compute_price": "percentage",
        #     })]
        # })
        #
        # cls.pricelist_chain_2 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - Center",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "pricelist",
        #         "compute_price": "formula",
        #     })]
        # })
        #
        # cls.pricelist_chain_1 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - Begin",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [],
        # })

    def test_70_items_ordering(self):
        return
        # pricelist with global/categ/template/product rules
        # some rules with minimal quantity
        # Ensure the good one is returned each time.

    def test_80_pricelist_constraints(self):
        return
        # check constraints (python (& sql correctly applied)) ?
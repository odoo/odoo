# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestPricelist(TransactionCase):

    def setUp(self):
        super(TestPricelist, self).setUp()

        self.datacard = self.env['product.product'].create({'name': 'Office Lamp'})
        self.usb_adapter = self.env['product.product'].create({'name': 'Office Chair'})
        self.uom_ton = self.env.ref('uom.product_uom_ton')
        self.uom_unit_id = self.ref('uom.product_uom_unit')
        self.uom_dozen_id = self.ref('uom.product_uom_dozen')
        self.uom_kgm_id = self.ref('uom.product_uom_kgm')

        self.public_pricelist = self.env.ref('product.list0')
        self.sale_pricelist_id = self.env['product.pricelist'].create({
            'name': 'Sale pricelist',
            'item_ids': [(0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_discount': 10,
                    'product_id': self.usb_adapter.id,
                    'applied_on': '0_product_variant',
                }), (0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_surcharge': -0.5,
                    'product_id': self.datacard.id,
                    'applied_on': '0_product_variant',
                })]
        })

    def test_10_discount(self):
        # Make sure the price using a pricelist is the same than without after
        # applying the computation manually
        context = {}

        public_context = dict(context, pricelist=self.public_pricelist.id)
        pricelist_context = dict(context, pricelist=self.sale_pricelist_id.id)

        usb_adapter_without_pricelist = self.usb_adapter.with_context(public_context)
        usb_adapter_with_pricelist = self.usb_adapter.with_context(pricelist_context)
        self.assertEqual(usb_adapter_with_pricelist.price, usb_adapter_without_pricelist.price*0.9)

        datacard_without_pricelist = self.datacard.with_context(public_context)
        datacard_with_pricelist = self.datacard.with_context(pricelist_context)
        self.assertEqual(datacard_with_pricelist.price, datacard_without_pricelist.price-0.5)

        # Make sure that changing the unit of measure does not break the unit
        # price (after converting)
        unit_context = dict(context, pricelist=self.sale_pricelist_id.id, uom=self.uom_unit_id)
        dozen_context = dict(context, pricelist=self.sale_pricelist_id.id, uom=self.uom_dozen_id)

        usb_adapter_unit = self.usb_adapter.with_context(unit_context)
        usb_adapter_dozen = self.usb_adapter.with_context(dozen_context)
        self.assertAlmostEqual(usb_adapter_unit.price*12, usb_adapter_dozen.price)
        datacard_unit = self.datacard.with_context(unit_context)
        datacard_dozen = self.datacard.with_context(dozen_context)
        # price_surcharge applies to product default UoM, here "Units", so surcharge will be multiplied
        self.assertAlmostEqual(datacard_unit.price*12, datacard_dozen.price)

    def test_20_pricelist_uom(self):
        # Verify that the pricelist rules are correctly using the product's default UoM
        # as reference, and return a result according to the target UoM (as specific in the context)

        kg, tonne = self.uom_kgm_id, self.uom_ton.id
        tonne_price = 100

        # make sure 'tonne' resolves down to 1 'kg'.
        self.uom_ton.write({'rounding': 0.001})
        # setup product stored in 'tonnes', with a discounted pricelist for qty > 3 tonnes
        spam_id = self.env['product.product'].create({
            'name': '1 tonne of spam',
            'uom_id': self.uom_ton.id,
            'uom_po_id': self.uom_ton.id,
            'list_price': tonne_price,
            'type': 'consu'
        })

        self.env['product.pricelist.item'].create({
            'pricelist_id': self.public_pricelist.id,
            'applied_on': '0_product_variant',
            'compute_price': 'formula',
            'base': 'list_price',  # based on public price
            'min_quantity': 3,  # min = 3 tonnes
            'price_surcharge': -10,  # -10 EUR / tonne
            'product_id': spam_id.id
        })
        pricelist = self.public_pricelist

        def test_unit_price(qty, uom, expected_unit_price):
            spam = spam_id.with_context({'uom': uom})
            unit_price = pricelist.with_context({'uom': uom}).get_product_price(spam, qty, False)
            self.assertAlmostEqual(unit_price, expected_unit_price, msg='Computed unit price is wrong')

        # Test prices - they are *per unit*, the quantity is only here to match the pricelist rules!
        test_unit_price(2, kg, tonne_price / 1000.0)
        test_unit_price(2000, kg, tonne_price / 1000.0)
        test_unit_price(3500, kg, (tonne_price - 10) / 1000.0)
        test_unit_price(2, tonne, tonne_price)
        test_unit_price(3, tonne, tonne_price - 10)

    def test_0_correct_pricelist_pulled_from_commercial_partner(self):
        """ Test that the correct pricelist is pulled from the commercial partner. """
        self.env['product.pricelist'].search([]).action_archive()
        default_pricelist = self.env['product.pricelist'].create({
            'name': 'Default Pricelist', 'sequence': 2
        })
        priority_pricelist = self.env['product.pricelist'].create({
            'name': 'Priority Pricelist', 'sequence': 1
        })

        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner',
            'country_id': self.env.ref('base.us').id,
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Child Partner',
            'parent_id': commercial_partner.id,
        })

        priority_pricelist.action_archive()

        print("parent: ", commercial_partner.property_product_pricelist.name)
        print("child: ", child_partner.property_product_pricelist.name)

        self.assertEqual(commercial_partner.property_product_pricelist, default_pricelist)
        # ==> should be default, is priority (which is archived)

        self.assertEqual(child_partner.property_product_pricelist, default_pricelist)
        # ==> should be its parent one, which should be default but is priority, but is default
        # (which is good... 2 Falses makes True =D)

    def test_1_correct_pricelist_pulled_from_commercial_partner(self):
        """ Test that the correct pricelist is pulled from the commercial partner. """
        self.env['product.pricelist'].search([]).action_archive()
        default_pricelist = self.env['product.pricelist'].create({
            'name': 'Default Pricelist', 'sequence': 2
        })
        restricted_pricelist = self.env['product.pricelist'].create({
            'name': 'Restricted Pricelist',
            'sequence': 1,
            'country_group_ids': [(6, 0, [self.env.ref('base.europe').id])],
        })

        restricted_pricelist.country_group_ids = []

        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner',
            'country_id': self.env.ref('base.us').id,
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Child Partner',
            'country_id': self.env.ref('base.us').id,
            'parent_id': commercial_partner.id,
        })

        print("parent: ", commercial_partner.property_product_pricelist.name)
        print("child: ", child_partner.property_product_pricelist.name)

        self.assertEqual(commercial_partner.property_product_pricelist, restricted_pricelist)
        self.assertEqual(child_partner.property_product_pricelist, restricted_pricelist)
        # ==> both should be the restricted since it's now available for all countries and has a
        # higher priority, but both are default one

    def test_2_correct_pricelist_pulled_from_commercial_partner(self):
        """ Test that the correct pricelist is pulled from the commercial partner. """
        self.env['product.pricelist'].search([]).action_archive()
        default_pricelist = self.env['product.pricelist'].create({
            'name': 'Default Pricelist', 'sequence': 2
        })
        restricted_pricelist = self.env['product.pricelist'].create({
            'name': 'Restricted Pricelist',
            'sequence': 1,
            'country_group_ids': [(6, 0, [self.env.ref('base.europe').id])],
        })

        restricted_pricelist.country_group_ids = []
        default_pricelist.action_archive()

        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner',
            'country_id': self.env.ref('base.us').id,
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Child Partner',
            'country_id': self.env.ref('base.us').id,
            'parent_id': commercial_partner.id,
        })

        print("parent: ", commercial_partner.property_product_pricelist.name)
        print("child: ", child_partner.property_product_pricelist.name)

        self.assertEqual(commercial_partner.property_product_pricelist, restricted_pricelist)
        self.assertEqual(child_partner.property_product_pricelist, restricted_pricelist)
        # OMG, this one is actually correct!

    def test_3_correct_pricelist_pulled_from_commercial_partner(self):
        """ Test that the correct pricelist is pulled from the commercial partner. """
        self.env['product.pricelist'].search([]).action_archive()
        default_pricelist = self.env['product.pricelist'].create({
            'name': 'Default Pricelist', 'sequence': 2
        })
        restricted_pricelist = self.env['product.pricelist'].create({
            'name': 'Restricted Pricelist',
            'sequence': 1,
            'country_group_ids': [(6, 0, [self.env.ref('base.europe').id])]
        })

        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner',
            'country_id': self.env.ref('base.us').id,
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Child Partner',
            'country_id': self.env.ref('base.us').id,
            'parent_id': commercial_partner.id,
        })

        restricted_pricelist.country_group_ids = []
        default_pricelist.action_archive()

        print("parent: ", commercial_partner.property_product_pricelist.name)
        print("child: ", child_partner.property_product_pricelist.name)

        self.assertEqual(commercial_partner.property_product_pricelist, restricted_pricelist)
        # ==> should be restricted since it's now available, is default, which is archived

        self.assertEqual(child_partner.property_product_pricelist, restricted_pricelist)
        # ==> should be its parent one, which should be restricted one but is default, but is restricted

        # ==> same result as 0

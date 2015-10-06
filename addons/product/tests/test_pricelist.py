# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestPricelist(TransactionCase):
    """Tests for unit of measure conversion"""

    def setUp(self):
        super(TestPricelist, self).setUp()
        self.ir_model_data = self.env['ir.model.data']
        self.product_product = self.env['product.product']
        self.product_pricelist = self.env['product.pricelist']
        self.uom = self.env['product.uom']

        self.usb_adapter_id = self.env.ref('product.product_product_48')
        self.datacard_id = self.env.ref('product.product_product_46')
        self.unit_id = self.env.ref('product.product_uom_unit')
        self.dozen_id = self.env.ref('product.product_uom_dozen')
        self.tonne_id = self.env.ref('product.product_uom_ton')
        self.kg_id = self.env.ref('product.product_uom_kgm')

        self.public_pricelist_id = self.env.ref('product.list0')
        self.sale_pricelist_id = self.product_pricelist.create({
            'name': 'Sale pricelist',
            'item_ids': [(0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_discount': 10,
                    'product_id': self.usb_adapter_id.id,
                    'applied_on': '0_product_variant',
                }), (0, 0, {
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_surcharge': -0.5,
                    'product_id': self.datacard_id.id,
                    'applied_on': '0_product_variant',
                })]
        })

    def test_10_discount(self):
        # Make sure the price using a pricelist is the same than without after
        # applying the computation manually
        context = {}

        public_context = dict(context, pricelist=self.public_pricelist_id.id)
        pricelist_context = dict(context, pricelist=self.sale_pricelist_id.id)

        usb_adapter_without_pricelist = self.usb_adapter_id.with_context(public_context)
        usb_adapter_with_pricelist = self.usb_adapter_id.with_context(pricelist_context)
        self.assertEqual(usb_adapter_with_pricelist.price, usb_adapter_without_pricelist.price*0.9)

        datacard_without_pricelist = self.datacard_id.with_context(public_context)
        datacard_with_pricelist = self.datacard_id.with_context(pricelist_context)
        self.assertEqual(datacard_with_pricelist.price, datacard_without_pricelist.price-0.5)

        # Make sure that changing the unit of measure does not break the unit
        # price (after converting)
        unit_context = dict(context, pricelist=self.sale_pricelist_id.id, uom=self.unit_id.id)
        dozen_context = dict(context, pricelist=self.sale_pricelist_id.id, uom=self.dozen_id.id)

        usb_adapter_unit = self.usb_adapter_id.with_context(unit_context)
        usb_adapter_dozen = self.usb_adapter_id.with_context(dozen_context)
        self.assertAlmostEqual(usb_adapter_unit.price*12, usb_adapter_dozen.price)
        datacard_unit = self.datacard_id.with_context(unit_context)
        datacard_dozen = self.datacard_id.with_context(dozen_context)
        # price_surcharge applies to product default UoM, here "Units", so surcharge will be multiplied
        self.assertAlmostEqual(datacard_unit.price*12, datacard_dozen.price)

    def test_20_pricelist_uom(self):
        # Verify that the pricelist rules are correctly using the product's default UoM
        # as reference, and return a result according to the target UoM (as specific in the context)

        kg, tonne = self.kg_id.id, self.tonne_id.id
        tonne_price = 100

        # make sure 'tonne' resolves down to 1 'kg'.
        self.tonne_id.write({'rounding': 0.001})
        # setup product stored in 'tonnes', with a discounted pricelist for qty > 3 tonnes
        spam_id = self.usb_adapter_id.copy({'name': '1 tonne of spam',
                                              'uom_id': self.tonne_id.id,
                                              'uom_po_id': self.tonne_id.id,
                                              'list_price': tonne_price,
                                              'product_type': 'consu',
                                            })
        self.env['product.pricelist.item'].create({'pricelist_id': self.public_pricelist_id.id,
                                                       'sequence': 10,
                                                       'applied_on': '0_product_variant',
                                                       'compute_price': 'formula',
                                                       'base': 'list_price',  # based on public price
                                                       'min_quantity': 3,  # min = 3 tonnes
                                                       'price_surcharge': -10,  # -10 EUR / tonne
                                                       'product_id': spam_id.id})
        pricelist_id = self.public_pricelist_id

        def test_unit_price(qty, uom, expected_unit_price):
            unit_price = pricelist_id.with_context({'uom': uom}).price_get(spam_id.id, qty)[pricelist_id.id]
            self.assertAlmostEqual(unit_price, expected_unit_price, msg='Computed unit price is wrong')

        # Test prices - they are *per unit*, the quantity is only here to match the pricelist rules!
        test_unit_price(2, kg, tonne_price / 1000.0)
        test_unit_price(2000, kg, tonne_price / 1000.0)
        test_unit_price(3500, kg, (tonne_price - 10) / 1000.0)
        test_unit_price(2, tonne, tonne_price)
        test_unit_price(3, tonne, tonne_price - 10)

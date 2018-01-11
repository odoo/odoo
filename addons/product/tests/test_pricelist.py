from openerp.tests.common import TransactionCase

class TestPricelist(TransactionCase):
    """Tests for unit of measure conversion"""

    def setUp(self):
        super(TestPricelist, self).setUp()
        cr, uid, context = self.cr, self.uid, {}
        self.ir_model_data = self.registry('ir.model.data')
        self.product_product = self.registry('product.product')
        self.product_pricelist = self.registry('product.pricelist')
        self.uom = self.registry('product.uom')

        self.usb_adapter_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_48')[1]
        self.datacard_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_46')[1]
        self.unit_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_uom_unit')[1]
        self.dozen_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_uom_dozen')[1]
        self.tonne_id = self.ir_model_data.xmlid_to_res_id(cr, uid, 'product.product_uom_ton')
        self.kg_id = self.ir_model_data.xmlid_to_res_id(cr, uid, 'product.product_uom_kgm')

        self.public_pricelist_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'list0')[1]
        self.sale_pricelist_id = self.product_pricelist.create(cr, uid, {
            'name': 'Sale pricelist',
            'type': 'sale',
            'version_id': [(0, 0, {
                'name': 'v1.0',
                'items_id': [(0, 0, {
                    'name': 'Discount 10%',
                    'base': 1, # based on public price
                    'price_discount': -0.1,
                    'product_id': self.usb_adapter_id
                }), (0, 0, {
                    'name': 'Discount -0.5',
                    'base': 1, # based on public price
                    'price_surcharge': -0.5,
                    'product_id': self.datacard_id
                })]
            })]
        }, context=context)

    def test_10_discount(self):
        # Make sure the price using a pricelist is the same than without after
        # applying the computation manually
        cr, uid, context = self.cr, self.uid, {}

        public_context = dict(context, pricelist=self.public_pricelist_id)
        pricelist_context = dict(context, pricelist=self.sale_pricelist_id)

        usb_adapter_without_pricelist = self.product_product.browse(cr, uid, self.usb_adapter_id, context=public_context)
        usb_adapter_with_pricelist = self.product_product.browse(cr, uid, self.usb_adapter_id, context=pricelist_context)
        self.assertEqual(usb_adapter_with_pricelist.price, usb_adapter_without_pricelist.price*0.9)

        datacard_without_pricelist = self.product_product.browse(cr, uid, self.datacard_id, context=public_context)
        datacard_with_pricelist = self.product_product.browse(cr, uid, self.datacard_id, context=pricelist_context)
        self.assertEqual(datacard_with_pricelist.price, datacard_without_pricelist.price-0.5)

        # Make sure that changing the unit of measure does not break the unit
        # price (after converting)
        unit_context = dict(context,
            pricelist=self.sale_pricelist_id,
            uom=self.unit_id)
        dozen_context = dict(context,
            pricelist=self.sale_pricelist_id,
            uom=self.dozen_id)

        usb_adapter_unit = self.product_product.browse(cr, uid, self.usb_adapter_id, context=unit_context)
        usb_adapter_dozen = self.product_product.browse(cr, uid, self.usb_adapter_id, context=dozen_context)
        self.assertAlmostEqual(usb_adapter_unit.price*12, usb_adapter_dozen.price)
        datacard_unit = self.product_product.browse(cr, uid, self.datacard_id, context=unit_context)
        datacard_dozen = self.product_product.browse(cr, uid, self.datacard_id, context=dozen_context)
        # price_surcharge applies to product default UoM, here "Units", so surcharge will be multiplied
        self.assertAlmostEqual(datacard_unit.price*12, datacard_dozen.price)

    def test_20_pricelist_uom(self):
        # Verify that the pricelist rules are correctly using the product's default UoM
        # as reference, and return a result according to the target UoM (as specific in the context)
        cr, uid = self.cr, self.uid
        kg, tonne = self.kg_id, self.tonne_id
        tonne_price = 100

        # make sure 'tonne' resolves down to 1 'kg'.
        self.uom.write(cr, uid, tonne, {'rounding': 0.001})

        # setup product stored in 'tonnes', with a discounted pricelist for qty > 3 tonnes
        spam_id = self.product_product.copy(cr, uid, self.usb_adapter_id,
                                            { 'name': '1 tonne of spam',
                                              'uom_id': self.tonne_id,
                                              'uos_id': self.tonne_id,
                                              'uom_po_id': self.tonne_id,
                                              'list_price': tonne_price,
                                            })
        pricelist_version_id = self.ir_model_data.xmlid_to_res_id(cr, uid, 'product.ver0')
        self.registry('product.pricelist.item').create(cr, uid,
                                                      { 'price_version_id': pricelist_version_id,
                                                        'sequence': 10,
                                                        'name': '3+ tonnes: -10 EUR discount/t',
                                                        'base': 1, # based on public price
                                                        'min_quantity': 3, # min = 3 tonnes
                                                        'price_surcharge': -10, # -10 EUR / tonne
                                                        'product_id': spam_id,
                                                      })
        pricelist_id = self.public_pricelist_id

        def test_unit_price(qty, uom, expected_unit_price):
            unit_price = self.registry('product.pricelist').price_get(cr, uid, [pricelist_id],
                                                                      spam_id, qty,
                                                                      context={'uom': uom})[pricelist_id]
            self.assertAlmostEqual(unit_price, expected_unit_price, msg='Computed unit price is wrong')

        # Test prices - they are *per unit*, the quantity is only here to match the pricelist rules!
        test_unit_price(2, kg, tonne_price / 1000.0)
        test_unit_price(2000, kg, tonne_price / 1000.0)
        test_unit_price(3500, kg, (tonne_price - 10) / 1000.0)
        test_unit_price(2, tonne, tonne_price)
        test_unit_price(3, tonne, tonne_price - 10)

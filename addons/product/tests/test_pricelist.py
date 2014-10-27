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
        self.assertAlmostEqual(datacard_unit.price*12, datacard_dozen.price)

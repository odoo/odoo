from odoo.addons.stock.tests.test_packing import TestPacking


class TestPacking(TestPacking):

    def setUp(self):
        super(TestPacking, self).setUp()
        self.uom_kg = self.env.ref('uom.product_uom_kgm')
        self.product_aw = self.env['product.product'].create({
            'name': 'Product AW',
            'type': 'product',
            'weight': 2.4,
            'uom_id': self.uom_kg.id,
            'uom_po_id': self.uom_kg.id
        })
        self.product_bw = self.env['product.product'].create({
            'name': 'Product BW',
            'type': 'product',
            'weight': 0.3,
            'uom_id': self.uom_kg.id,
            'uom_po_id': self.uom_kg.id
        })
        test_carrier_product = self.env['product.product'].create({
            'name': 'Test carrier product',
            'type': 'service',
        })
        self.test_carrier = self.env['delivery.carrier'].create({
            'name': 'Test carrier',
            'delivery_type': 'fixed',
            'product_id': test_carrier_product.id,
        })

    def test_put_in_pack_weight_wizard(self):
        """ Check that de default weight is correctly set by default when using the 'choose.delivery.package' wizard.
        This purpose of this wizard is
        """
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 20.0)
        self.env['stock.quant']._update_available_quantity(self.product_bw, self.stock_location, 20.0)

        picking_ship = self.env['stock.picking'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        move_line_paw = self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'qty_done': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        move_line_pbw = self.env['stock.move.line'].create({
            'product_id': self.product_bw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'qty_done': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        picking_ship.action_confirm()
        pack_action = picking_ship.put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']

        # We make sure the correct action was returned
        self.assertEquals(pack_action_model, 'choose.delivery.package')

        # We instanciate the wizard with the context of the action and check that the
        # default weight was set.
        pack_wiz = self.env['choose.delivery.package'].with_context(pack_action_ctx).create({})
        self.assertEquals(pack_wiz.shipping_weight, 13.5)

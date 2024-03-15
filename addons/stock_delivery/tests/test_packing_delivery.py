# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.test_packing import TestPackingCommon
from odoo.exceptions import UserError
from odoo.tests import Form
from unittest.mock import patch


class TestPacking(TestPackingCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPacking, cls).setUpClass()
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.product_aw = cls.env['product.product'].create({
            'name': 'Product AW',
            'type': 'product',
            'weight': 2.4,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id
        })
        cls.product_bw = cls.env['product.product'].create({
            'name': 'Product BW',
            'type': 'product',
            'weight': 0.3,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id
        })
        test_carrier_product = cls.env['product.product'].create({
            'name': 'Test carrier product',
            'type': 'service',
        })
        cls.test_carrier = cls.env['delivery.carrier'].create({
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
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_bw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        pack_action = picking_ship.action_put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']

        # We make sure the correct action was returned
        self.assertEqual(pack_action_model, 'choose.delivery.package')

        # We instanciate the wizard with the context of the action and check that the
        # default weight was set.
        pack_wiz = self.env['choose.delivery.package'].with_context(pack_action_ctx).create({})
        self.assertEqual(pack_wiz.shipping_weight, 13.5)

    def test_send_to_shipper_without_sale_order(self):
        """
            Check we can validate delivery with a delivery carrier set when it isn't linked to a sale order
        """
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 20.0)

        picking_ship = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        self.assertEqual(picking_ship.state, 'assigned', 'Delivery state should be assigned.')
        self.assertFalse(picking_ship.sale_id.id, 'Sale order shouldn\'t be set')
        picking_ship.move_ids.picked = True
        picking_ship.button_validate()
        self.assertEqual(picking_ship.state, 'done')

    def test_multistep_delivery_tracking(self):
        # Set Warehouse as multi steps delivery
        self.warehouse.delivery_steps = "pick_pack_ship"

        # Create and confirm the SO
        so = self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.env['res.partner'].create({'name': 'Rando le clodo'}).id,
            'order_line': [
                (0, 0, {'name': self.product_aw.name, 'product_id': self.product_aw.id, 'product_uom_qty': 1, 'price_unit': 1})
            ]
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.test_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        so.action_confirm()

        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 20.0)

        # Confirm the picking and send to shipper
        picking_ship = so.picking_ids.filtered(lambda p: p.picking_type_id.name == 'Pick')
        picking_ship.action_confirm()
        picking_ship.move_ids.quantity = 1.0
        picking_ship.move_ids.picked = True
        picking_ship.button_validate()

        # Mock carrier shipping method
        with patch(
            'odoo.addons.stock_delivery.models.delivery_carrier.DeliveryCarrier.fixed_send_shipping',
            return_value=[{'exact_price': 0, 'tracking_number': "666"}]
        ):
            picking_ship.send_to_shipper()

        for p in so.picking_ids:
            self.assertEqual(p.carrier_tracking_ref, "666")

    def test_batch_picking_delivery(self):
        """
            Check that when Put in Pack is called for batch pickings (i.e. faked with multi-record action
            calling to avoid extra batch+delivery module for just a test) then:
             - Same delivery carrier = works
             - Different delivery carriers = UserError
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 4.0)
        another_test_carrier_product = self.env['product.product'].create({
            'name': 'Another test carrier product',
            'type': 'service',
        })
        test_carrier = self.env['delivery.carrier'].create({
            'name': 'Another Test carrier',
            'delivery_type': 'fixed',
            'product_id': another_test_carrier_product.id,
        })

        delivery_1 = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        ml_1 = self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': delivery_1.id,
            'quantity': 1,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })

        # Test that differing carrier + put in pack = UserError
        delivery_2 = delivery_1.copy({'carrier_id': test_carrier.id})
        ml_1.copy({'picking_id': delivery_2.id, 'quantity': 1})
        # recreate the `action_put_in_pack`` steps so we don't have to add test to new module for batch pickings
        # to use batch version of method (which bypass the ensure_one() check in the stock_picking action)
        move_lines_to_pack = (delivery_1 | delivery_2)._package_move_lines()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        with self.assertRaises(UserError):
            delivery_1._pre_put_in_pack_hook(move_lines_to_pack)

        # Test that same carrier + put in pack = OK!
        delivery_2.carrier_id = delivery_1.carrier_id
        move_lines_to_pack = (delivery_1 | delivery_2)._package_move_lines()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        delivery_1._pre_put_in_pack_hook(move_lines_to_pack)
        package = delivery_1._put_in_pack(move_lines_to_pack)
        self.assertEqual(delivery_1.move_line_ids.result_package_id, package, 'Delivery 1 moves should have been put in package.')
        self.assertEqual(delivery_2.move_line_ids.result_package_id, package, 'Delivery 2 moves should have been put in package.')

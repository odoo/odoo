# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
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
            'is_storable': True,
            'weight': 2.4,
            'uom_id': cls.uom_kg.id,
        })
        cls.product_bw = cls.env['product.product'].create({
            'name': 'Product BW',
            'is_storable': True,
            'weight': 0.3,
            'uom_id': cls.uom_kg.id,
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
        """ Check that de default weight is correctly set by default when using the 'stock.put.in.pack' wizard.
        This purpose of this wizard is to set the delivery package type and weight before validating the package.
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
        move_line = self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picked': True,
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_bw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picked': True,
        })
        self.assertEqual(picking_ship.shipping_weight, 13.5)  # 2.4 * 5 + 0.3 * 5
        pack_action = picking_ship.action_put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']

        # We make sure the correct action was returned
        self.assertEqual(pack_action_model, 'stock.put.in.pack')

        # We instanciate the wizard with the context of the action and check that the
        # default weight was set.
        pack_wiz = self.env['stock.put.in.pack'].with_context(pack_action_ctx).create({})
        self.assertEqual(pack_wiz.shipping_weight, 13.5)

        # unpick the move lines and check that the weight is correctly updated
        move_line.write({'picked': False})

        pack_action = picking_ship.action_put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']
        self.assertEqual(pack_action_model, 'stock.put.in.pack')

        pack_wiz = self.env['stock.put.in.pack'].with_context(pack_action_ctx).create({})
        self.assertEqual(pack_wiz.shipping_weight, 1.5)
        pack_wiz.shipping_weight = 5
        pack_wiz.action_put_in_pack()

        self.assertEqual(picking_ship.shipping_weight, 17)  # 2.4 * 5 + 5

    def test_pack_in_pack_weight_wizard(self):
        """ Check that de default weight is correctly set by default when using the 'stock.put.in.pack' wizard on packages.
        """
        package_type = self.env['stock.package.type'].create({'name': 'Locked Box'})
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 5.0)
        self.env['stock.quant']._update_available_quantity(self.product_bw, self.stock_location, 5.0)

        delivery = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_aw.id,
                    'product_uom_qty': 5,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                }),
                Command.create({
                    'product_id': self.product_bw.id,
                    'product_uom_qty': 5,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                }),
            ],
        })
        delivery.action_confirm()
        self.assertEqual(delivery.shipping_weight, 13.5)  # 2.4 * 5 + 0.3 * 5

        # Picks the first product (aw) and put it in a pack
        delivery.move_ids.filtered(lambda m: m.product_id == self.product_aw).picked = True
        wizard = Form.from_action(self.env, delivery.action_put_in_pack())
        self.assertEqual(wizard.shipping_weight, 12)  # 2.4 * 5
        wizard.package_type_id = package_type
        wizard.shipping_weight = 15
        wizard.save().action_put_in_pack()
        self.assertEqual(delivery.shipping_weight, 16.5)  # 15 + 0.3 * 5

        # Picks the second product (bw) and put in in a pack
        delivery.move_ids.picked = True
        wizard = Form.from_action(self.env, delivery.action_put_in_pack())
        self.assertEqual(wizard.shipping_weight, 1.5)  # 0.3 * 5
        wizard.package_type_id = package_type
        wizard.shipping_weight = 3
        wizard.save().action_put_in_pack()
        self.assertEqual(delivery.shipping_weight, 18)  # 15 + 3

        # Pack both packages into a new package
        wizard = Form.from_action(self.env, delivery.action_put_in_pack())
        self.assertEqual(wizard.shipping_weight, 18)  # 15 + 3
        wizard.package_type_id = package_type
        wizard.shipping_weight = 20
        wizard.save().action_put_in_pack()
        self.assertEqual(delivery.shipping_weight, 20)

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
        move_lines_to_pack, __ = (delivery_1 | delivery_2).move_line_ids._get_lines_and_packages_to_pack()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        with self.assertRaises(UserError):
            move_lines_to_pack._pre_put_in_pack_hook()

        # Test that same carrier + put in pack = OK!
        delivery_2.carrier_id = delivery_1.carrier_id
        move_lines_to_pack, __ = (delivery_1 | delivery_2).move_line_ids._get_lines_and_packages_to_pack()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        move_lines_to_pack._pre_put_in_pack_hook()
        package = move_lines_to_pack._put_in_pack()
        self.assertEqual(delivery_1.move_line_ids.result_package_id, package, 'Delivery 1 moves should have been put in package.')
        self.assertEqual(delivery_2.move_line_ids.result_package_id, package, 'Delivery 2 moves should have been put in package.')

    def test_picking_access_error_on_package(self):
        """ In a multi-company environment, a reusable package which is used by 2+ companies can cause access errors
        on a company's picking history when it is in an in-use state (waiting to be unpacked)
        """
        company_a_user = self.env['res.users'].create({
            'name': 'test user company a',
            'login': 'test@testing.testing',
            'password': 'password',
            'group_ids': [Command.set([self.env.ref('stock.group_stock_user').id])],
        })
        wh_a = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        wh_a.delivery_steps = 'pick_pack_ship'
        company_b = self.env['res.company'].create({'name': 'Company B'})
        wh_b = self.env['stock.warehouse'].with_company(company_b).create({
            'name': 'Company B WH',
            'code': 'WH B',
            'delivery_steps': 'pick_pack_ship',
            'company_id': company_b.id,
        })
        reusable_type = self.env['stock.package.type'].create({
            'name': 'Reusable',
            'package_use': 'reusable',
        })
        reusable_box = self.env['stock.package'].create({
            'name': 'Reusable Box',
            'package_type_id': reusable_type.id,
        })

        delivery_company_a = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [Command.create({
                'product_id': self.productA.id,
                'product_uom_qty': 5.0,
                'location_id': self.stock_location.id,
                'product_uom': self.productA.uom_id.id,
                'location_dest_id': self.customer_location.id,
            })],
            'move_line_ids': [Command.create({
                'location_id': self.stock_location.id,
                'result_package_id': reusable_box.id,
                'quantity': 5.0,
                'product_id': self.productA.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.productA.uom_id.id,
            })],
        })
        delivery_company_a.action_confirm()
        delivery_company_a.move_ids.quantity = 5.0
        delivery_company_a.button_validate()
        reusable_box.unpack()

        other_picking_company_b = self.env['stock.picking'].with_company(company_b).create({
            'picking_type_id': wh_b.int_type_id.id,
            'location_id': wh_b.lot_stock_id.id,
            'location_dest_id': wh_b.lot_stock_id.id,
            'move_ids': [Command.create({
                'product_id': self.productA.id,
                'product_uom_qty': 3.0,
                'location_id': wh_b.lot_stock_id.id,
                'location_dest_id': wh_b.lot_stock_id.id,
                'product_uom': self.productA.uom_id.id,
            })],
            'move_line_ids': [Command.create({
                'location_id': wh_b.lot_stock_id.id,
                'location_dest_id': wh_b.lot_stock_id.id,
                'result_package_id': reusable_box.id,
                'quantity': 3.0,
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
            })],
        })
        other_picking_company_b.action_confirm()
        other_picking_company_b.move_ids.quantity = 3.0
        other_picking_company_b.button_validate()

        company_a_user.group_ids = [Command.unlink(self.env.ref('stock.group_stock_multi_warehouses').id)]
        res = delivery_company_a.with_user(company_a_user).read()
        self.assertTrue(res)

    def test_put_in_pack_applies_only_to_selected_move_line(self):
        """Ensure that the 'Put in Pack' action applies only to the selected
        stock move line, without affecting other move lines in the same picking.
        """
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 5.0)
        self.env['stock.quant']._update_available_quantity(self.product_bw, self.stock_location, 5.0)

        picking_ship = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        move_line_1 = self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picked': True,
        })
        move_line_2 = self.env['stock.move.line'].create({
            'product_id': self.product_bw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picked': True,
        })
        pack_action = move_line_1.action_put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']
        # Ensure the correct wizard action is returned
        self.assertEqual(pack_action_model, 'stock.put.in.pack')
        pack_wiz = self.env['stock.put.in.pack'].with_context(pack_action_ctx).create({})
        pack_wiz.action_put_in_pack()
        self.assertTrue(move_line_1.result_package_id, 'A package should have been created for the selected move line')
        self.assertFalse(move_line_2.result_package_id, 'The other move line should not be packed')

    def test_multi_level_package_weight(self):
        self.warehouse.delivery_steps = 'ship_only'
        self.productA.weight = 2
        self.productB.weight = 5
        sbox_type, bbox_type, pallet_type = self.env['stock.package.type'].create([{
            'name': name,
            'base_weight': weight,
        } for (name, weight) in [('Smol Box', 1), ('Big Box', 4), ('pallet', 10)]])
        boxA, boxB, big_box, pallet = self.env['stock.package'].create([{
            'package_type_id': pack_type.id
        } for pack_type in [sbox_type, sbox_type, bbox_type, pallet_type]])

        # Content of packages:
        # Pallet              (base  10kg) -> 46kg
        # └ 1x Product B      (1*5 =  5kg)
        # └ Big Box           (base   4kg) -> 31kg
        #   └ Box A           (base   1kg) -> 11kg
        #     └ 5x Product A  (5*2 = 10kg)
        #   └ Box B           (base   1kg) -> 16kg
        #     └ 3x Product B  (3*5 = 15kg)
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 5, package_id=boxA)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 3, package_id=boxB)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 1, package_id=pallet)
        (boxA | boxB).parent_package_id = big_box
        big_box.parent_package_id = pallet

        self.assertEqual(boxA.weight, 11)
        self.assertEqual(boxB.weight, 16)
        self.assertEqual(big_box.weight, 31)
        self.assertEqual(pallet.weight, 46)

        # Now check that the weight is correctly computed for ongoing pickings
        delivery = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [
                Command.create({
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'product_id': self.productA.id,
                    'product_uom_qty': 2,
                }),
                Command.create({
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'product_id': self.productB.id,
                    'product_uom_qty': 2,
                }),
            ],
        })
        delivery.action_confirm()
        res_boxA = delivery.move_ids[0].move_line_ids.action_put_in_pack(package_type_id=sbox_type.id)
        res_boxB = delivery.move_ids[1].move_line_ids.action_put_in_pack(package_type_id=sbox_type.id)
        res_big_box = delivery.move_ids.move_line_ids.action_put_in_pack(package_type_id=bbox_type.id)
        res_pallet = delivery.move_ids.move_line_ids.action_put_in_pack(package_type_id=pallet_type.id)

        self.assertEqual(res_boxA.with_context(picking_id=delivery.id).weight, 5)      # 1 + 2 * 2 = 5kg
        self.assertEqual(res_boxB.with_context(picking_id=delivery.id).weight, 11)     # 1 + 2 * 5 = 11kg
        self.assertEqual(res_big_box.with_context(picking_id=delivery.id).weight, 20)  # 4 + 5 + 11 = 20kg
        self.assertEqual(res_pallet.with_context(picking_id=delivery.id).weight, 30)   # 10 + 20 = 30kg

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo.fields import Command, Datetime
from odoo.tests import Form
from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


class TestRentalKits(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

        cls.component_1 = cls.env['product.product'].create({'name': 'compo 1', 'is_storable': True})
        cls.component_2 = cls.env['product.product'].create({'name': 'compo 2', 'is_storable': True})
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_id.id,
            'product_tmpl_id': cls.product_id.product_tmpl_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.component_2.id, 'product_qty': 2})
            ]
        })

        quants = cls.env['stock.quant'].create({
            'product_id': cls.component_1.id,
            'inventory_quantity': 5.0,
            'location_id': cls.warehouse_id.lot_stock_id.id
        })
        quants |= cls.env['stock.quant'].create({
            'product_id': cls.component_2.id,
            'inventory_quantity': 10.0,
            'location_id': cls.warehouse_id.lot_stock_id.id
        })
        quants.action_apply_inventory()

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_line_1 = rental_order_1.order_line
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(len(rental_order_1.picking_ids.move_ids), 4)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'waiting')
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [4.0, 8.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [4.0, 8.0])

        rental_order_1.order_line.write({'product_uom_qty': 2})
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [2.0, 4.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [2.0, 4.0])

        outgoing_picking.move_ids[0].quantity = 1
        outgoing_picking.move_ids[1].quantity = 2
        Form.from_action(self.env, outgoing_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)
        self.env.add_to_compute(rental_line_1._fields['qty_delivered'], rental_line_1)
        self.assertEqual(
            rental_line_1.qty_delivered, 1,
            "Quantity delivered shouldn't change after recompute",
        )

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing')
        self.assertEqual(outgoing_picking_2.move_ids.mapped('product_uom_qty'), [1.0, 2.0])
        rental_order_1.order_line.write({'product_uom_qty': 3})
        self.assertEqual(outgoing_picking_2.move_ids.mapped('product_uom_qty'), [2.0, 4.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])
        incoming_picking.action_assign()
        self.assertEqual(incoming_picking.move_ids.mapped('quantity'), [1.0, 2.0])

        outgoing_picking_2.move_ids[0].quantity = 1
        outgoing_picking_2.move_ids[1].quantity = 2
        Form.from_action(self.env, outgoing_picking_2.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)
        self.env.add_to_compute(rental_line_1._fields['qty_delivered'], rental_line_1)
        self.assertEqual(
            rental_line_1.qty_delivered, 2,
            "Quantity delivered shouldn't change after recompute",
        )

        incoming_picking.move_ids[0].quantity = 1
        incoming_picking.move_ids[1].quantity = 2
        Form.from_action(self.env, incoming_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'incoming')
        self.assertEqual(incoming_picking_2.move_ids.mapped('product_uom_qty'), [2.0, 4.0])

        outgoing_picking_3.button_validate()
        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)

    def test_late_fee(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() - timedelta(days=7)
        rental_order_1.rental_return_date = Datetime.now() - timedelta(days=3)
        rental_order_1.action_confirm()

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(outgoing_picking.scheduled_date.date(), rental_order_1.rental_start_date.date())
        outgoing_picking.button_validate()

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking.move_ids[0].picked = True
        Form.from_action(self.env, incoming_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 0)
        self.assertEqual(len(rental_order_1.order_line), 1)

        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking_2.move_ids[0].quantity = 2
        incoming_picking_2.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_subkits_and_same_component(self):
        """
        - Kit
            - 1 x C1
                - 1 x C2
                - 1 x C3
            - 2X C2

        Rental with delivery
        Ensure that qties of both delivery and return are correct
        """
        stock_location = self.warehouse_id.lot_stock_id
        rental_location = self.env.company.rental_loc_id

        component_3 = self.env['product.product'].create({
            'name': 'compo 3',
            'type': 'consu',
        })

        sub_bom = self.env['mrp.bom'].create({
            'product_id': self.component_1.id,
            'product_tmpl_id': self.component_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': component_3.id, 'product_qty': 1})
            ]
        })
        _bom_line_01, bom_line_02 = self.bom.bom_line_ids
        bom_line_03, bom_line_04 = sub_bom.bom_line_ids

        rental = self.sale_order_id.copy()
        rental.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental.action_confirm()

        # The BoM line sequence should be respected when exploding a BoM that contains a kit.
        self.assertRecordValues(rental.picking_ids.move_ids, [
            {'product_id': self.component_2.id, 'product_qty': 1, 'bom_line_id': bom_line_03.id, 'location_id': stock_location.id},
            {'product_id': component_3.id, 'product_qty': 1, 'bom_line_id': bom_line_04.id, 'location_id': stock_location.id},
            {'product_id': self.component_2.id, 'product_qty': 2, 'bom_line_id': bom_line_02.id, 'location_id': stock_location.id},
            {'product_id': self.component_2.id, 'product_qty': 1, 'bom_line_id': bom_line_03.id, 'location_id': rental_location.id},
            {'product_id': component_3.id, 'product_qty': 1, 'bom_line_id': bom_line_04.id, 'location_id': rental_location.id},
            {'product_id': self.component_2.id, 'product_qty': 2, 'bom_line_id': bom_line_02.id, 'location_id': rental_location.id},
        ])

    def test_pickup_kit_from_rental(self):
        """Create a rental with a kit and confirm it. Then, pickup the kit.
        """
        # disable the setting to don't create a picking and allow the user to pickup the kit
        self.env.user.groups_id -= self.env.ref('sale_stock_renting.group_rental_stock_picking')
        settings = self.env['res.config.settings'].with_user(self.env.user).create({})
        settings.group_rental_stock_picking = False
        settings.set_values()
        # create a rental with kit
        rental = self.sale_order_id.copy()
        rental.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        self.assertEqual(rental.order_line.product_id.is_kits, True)
        rental.action_confirm()
        # pickup the kit
        self.assertEqual(rental.order_line.qty_delivered, 0)
        action_dict = rental.action_open_pickup()
        pickup_wizard = self.env['rental.order.wizard'].with_context(
            action_dict['context']
        ).create({})
        pickup_wizard._get_wizard_lines()
        pickup_wizard.apply()
        self.assertEqual(rental.order_line.qty_delivered, 1)

    def test_kit_multipick_flow(self):
        """
        Test that confirming a rental order with a kit product whose components
        use two different pack locations does not crash when assigning a return_id.
        Two pick operations are generated (one per pack location).
        """
        self.warehouse_id.delivery_steps = 'pick_pack_ship'

        # Locations
        customer_location = self.env.ref('stock.stock_location_customers')
        output_location = self.env.ref('stock.stock_location_output')
        pack_location_copy = self.env.ref('stock.location_pack_zone').copy()

        # Create a new pick operation
        pick_operation_copy = self.warehouse_id.pick_type_id.copy({'default_location_dest_id': pack_location_copy.id})

        # Create a new route to use the new pick operation
        custom_route = self.env['stock.route'].create({
            'name': 'Test',
            'rule_ids': [
                Command.create({
                    'name': 'test 1',
                    'action': 'pull',
                    'picking_type_id': pick_operation_copy.id,
                    'location_src_id': self.warehouse_id.lot_stock_id.id,
                    'location_dest_id': customer_location.id,
                }),
                Command.create({
                    'name': 'test 2',
                    'action': 'push',
                    'picking_type_id': self.warehouse_id.pack_type_id.id,
                    'location_src_id': pack_location_copy.id,
                    'location_dest_id': output_location.id,
                }),
                Command.create({
                    'name': 'test 3',
                    'action': 'push',
                    'picking_type_id': self.warehouse_id.out_type_id.id,
                    'location_src_id': output_location.id,
                    'location_dest_id': customer_location.id,
                }),
            ],
        })

        # Add the route to a component product
        self.component_1.route_ids = [Command.link(custom_route.id)]

        # create a rental with the kit product
        rental = self.sale_order_id.copy()
        rental.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        self.assertEqual(rental.order_line.product_id.is_kits, True)
        rental.action_confirm()

        picks = rental.picking_ids.filtered(lambda pick: pick.picking_type_id in (pick_operation_copy, self.warehouse_id.pick_type_id))
        self.assertEqual(len(picks), 2)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form


class TestWarehouseMrp(common.TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.graphics_card = cls.env['product.product'].create({
            'name': 'Individual Workplace',
            'uom_id': cls.uom_unit.id,
            'type': 'consu',
            'is_storable': True,
            'tracking': 'none',
        })
        cls.laptop = cls.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'uom_id': cls.uom_unit.id,
            'type': 'consu',
            'is_storable': True,
            'tracking': 'none',
        })
        cls.depot_location = cls.env['stock.location'].create({
            'name': 'Depot',
            'usage': 'internal',
            'location_id': cls.stock_location.id,
        })
        cls.env["stock.putaway.rule"].create({
            "location_in_id": cls.stock_location.id,
            "location_out_id": cls.depot_location.id,
        })
        cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.env['stock.quant'].create({
            'location_id': cls.shelf_1.id,
            'product_id': cls.graphics_card.id,
            'inventory_quantity': 16.0
        }).action_apply_inventory()

        cls.bom_laptop = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': cls.uom_unit.id,
            'consumption': 'flexible',
            'bom_line_ids': [Command.create({
                'product_id': cls.graphics_card.id,
                'product_qty': 1,
                'product_uom_id': cls.uom_unit.id
            })],
            'operation_ids': [Command.create({
                'name': 'Cutting Machine',
                'workcenter_id': cls.workcenter_1.id,
                'time_cycle': 12,
                'sequence': 1,
            })],
        })

    def new_mo_laptop(self):
        form = Form(self.env['mrp.production'])
        form.product_id = self.laptop
        form.product_qty = 1
        form.bom_id = self.bom_laptop
        p = form.save()
        p.action_confirm()
        p.action_assign()
        return p

    def test_manufacturing_route(self):
        warehouse_1_stock_manager = self.warehouse_1.with_user(self.user_stock_manager)
        manu_rule = self.env['stock.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        manu_route = manu_rule.route_id
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.manufacture_to_resupply = False
        self.assertFalse(self.warehouse_1.manufacture_pull_id.active)
        self.assertFalse(self.picking_type_manu.active)
        self.assertNotIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.manufacture_to_resupply = True
        manu_rule = self.env['stock.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        self.assertTrue(self.picking_type_manu.active)
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())

    def test_manufacturing_rule_other_dest(self):
        """ Ensures that a manufacturing rule can define a destination the rule itself and have it
            applied instead of the one from the operation type if location_dest_from_rule is set.
        """
        freezer_loc = self.env['stock.location'].create({
            'name': 'Freezer',
            'location_id': self.warehouse_1.view_location_id.id,
        })
        route = self.env['stock.route'].create({
            'name': 'Manufacture then freeze',
            'rule_ids': [
                Command.create({
                    'name': 'Freezer -> Stock',
                    'action': 'pull',
                    'procure_method': 'make_to_order',
                    'picking_type_id': self.warehouse_1.int_type_id.id,
                    'location_src_id': freezer_loc.id,
                    'location_dest_id': self.warehouse_1.lot_stock_id.id,
                    'location_dest_from_rule': True,
                }),
                Command.create({
                    'name': 'Manufacture',
                    'action': 'manufacture',
                    'picking_type_id': self.warehouse_1.manu_type_id.id,
                    'location_src_id': self.warehouse_1.lot_stock_id.id,
                    'location_dest_id': freezer_loc.id,
                    'location_dest_from_rule': True,
                }),
            ],
        })
        # Remove the classic Manufacture route if it exists and replace it by the new one
        self.product_4.route_ids = [
            Command.link(route.id),
            Command.unlink(self.warehouse_1.manufacture_pull_id.id),
        ]

        # Create a procurement to resupply the Stock, taking from the Freezer.
        self.env['stock.rule'].run([
            self.env['stock.rule'].Procurement(
                self.product_4,
                5.0,
                self.product_4.uom_id,
                self.warehouse_1.lot_stock_id,
                'test_other_dest',
                'test_other_dest',
                self.warehouse_1.company_id,
                {
                    'warehouse_id': self.warehouse_1,
                }
            )
        ])

        # Make sure the production is delivering the goods in the location set on the rule.
        production = self.env['mrp.production'].search([('product_id', '=', self.product_4.id)])
        self.assertEqual(len(production), 1)
        self.assertEqual(production.picking_type_id.default_location_dest_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(production.location_dest_id, freezer_loc)

    def test_multi_warehouse_resupply(self):
        """ test a multi warehouse flow give a correct date delay
            product_6 is sold from warehouse_1, its component (product_4) is
            resupplied from warehouse_2 and manufactured in warehouse_2.
            Everything in mto """

        self.route_mto.active = True
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2',
        })
        # product 4 can only be manufacture in WH2
        self.bom_1.picking_type_id = warehouse_2.manu_type_id

        self.warehouse_1.manufacture_steps = "pbm"
        self.warehouse_1.resupply_wh_ids = [Command.set([warehouse_2.id])]
        self.product_6.route_ids = [Command.set([self.route_manufacture.id, self.route_mto.id])]
        self.product_4.route_ids = [Command.set([
            self.warehouse_1.resupply_route_ids.id,
            self.route_mto.id,
        ])]
        warehouse_2.resupply_route_ids.rule_ids.procure_method = 'make_to_order'

        self.env['stock.rule'].run([
            self.env['stock.rule'].Procurement(
                self.product_6,
                5.0,
                self.product_6.uom_id,
                self.customer_location,
                'test_ressuply',
                'test_ressuply',
                self.warehouse_1.company_id,
                {
                    'warehouse_id': self.warehouse_1,
                },
            ),
        ])

    def test_manufacturing_scrap(self):
        """
            Testing to do a scrap of consumed material.
        """

        # Update demo products
        (self.product_4 | self.product_2).write({
            'tracking': 'lot',
        })

        # Update Bill Of Material to remove product with phantom bom.
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()

        # Create Inventory Adjustment For Stick and Stone Tools with lot.
        lot_product_4 = self.env['stock.lot'].create({
            'name': '0000000000001',
            'product_id': self.product_4.id,
        })
        lot_product_2 = self.env['stock.lot'].create({
            'name': '0000000000002',
            'product_id': self.product_2.id,
        })

        # Inventory for Stick
        self.env['stock.quant'].create({
            'location_id': self.shelf_1.id,
            'product_id': self.product_4.id,
            'inventory_quantity': 8,
            'lot_id': lot_product_4.id
        }).action_apply_inventory()

        # Inventory for Stone Tools
        self.env['stock.quant'].create({
            'location_id': self.shelf_1.id,
            'product_id': self.product_2.id,
            'inventory_quantity': 12,
            'lot_id': lot_product_2.id
        }).action_apply_inventory()

        #Create Manufacturing order.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_3
        production_form.product_qty = 12
        production_form.product_uom_id = self.product_6.uom_id
        production_3 = production_form.save()
        production_3.action_confirm()
        production_3.action_assign()

        # Check Manufacturing order's availability.
        self.assertEqual(production_3.reservation_state, 'assigned', "Production order's availability should be Available.")

        location_id = production_3.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) and production_3.location_src_id.id or production_3.location_dest_id.id,

        # Scrap Product Wood without lot to check assert raise ?.
        scrap_id = self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'production_id': production_3.id})
        with self.assertRaises(UserError):
            scrap_id.do_scrap()

        # Scrap Product Wood with lot.
        scrap_id = self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'lot_id': lot_product_2.id, 'production_id': production_3.id})
        scrap_id.do_scrap()
        scrap_move = scrap_id.move_ids[0]

        self.assertTrue(scrap_move.raw_material_production_id)
        self.assertEqual(scrap_move.location_dest_usage, 'inventory')
        self.assertEqual(scrap_move.location_dest_id, scrap_id.scrap_location_id)
        self.assertEqual(scrap_move.price_unit, scrap_move.product_id.standard_price)

        #Check scrap move is created for this production order.
        #TODO: should check with scrap objects link in between

#        scrap_move = production_3.move_raw_ids.filtered(lambda x: x.product_id == self.product_2 and x.location_dest_usage == 'inventory')
#        self.assertTrue(scrap_move, "There are no any scrap move created for production order.")

    def test_putaway_after_manufacturing_3(self):
        """ This test checks a tracked manufactured product will go to location
        defined in putaway strategy when the production is recorded with
        product.produce wizard.
        """
        self.laptop.tracking = 'serial'
        mo_laptop = self.new_mo_laptop()
        serial = self.env['stock.lot'].create({'product_id': self.laptop.id})

        mo_form = Form(mo_laptop)
        mo_form.lot_producing_ids.set(serial)
        mo_laptop = mo_form.save()
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)

    def test_backorder_unpacking(self):
        """ Test that movement of pack in backorder is correctly handled. """
        self.warehouse_1.manufacture_steps = 'pbm'

        self.product_1.is_storable = True
        self.env['stock.quant']._update_available_quantity(self.product_1, self.stock_location, 100)

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo_form.product_qty = 100
        mo = mo_form.save()
        mo.action_confirm()

        package = self.env['stock.package'].create({})

        picking = mo.picking_ids
        picking.move_line_ids.write({
            'quantity': 20,
            'result_package_id': package.id,
        })

        Form.from_action(self.env, picking.button_validate()).save().process()

        backorder = picking.backorder_ids
        backorder.move_line_ids.quantity = 80
        backorder.button_validate()

        self.assertEqual(picking.state, 'done')
        self.assertEqual(backorder.state, 'done')
        self.assertEqual(mo.move_raw_ids.move_line_ids.mapped('quantity_product_uom'), [20, 80])

    def test_produce_with_zero_available_qty(self):
        """ Test that producing with 0 qty_available for the component
        still links the stock.move.line to the production order. """
        mo, *_ = self.generate_mo()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.move_line_ids.production_id, mo)

    def test_unarchive_mto_route_active_needed_rules_only(self):
        """ Ensure that activating a route will activate only its relevant rules.
            Here, unarchiving the MTO route shouldn't active pull rule for the Pre-Production
            location if manufacture is in 1 step since this location is archived.
        """

        self.env.user.group_ids += self.env.ref('stock.group_adv_location')

        # initially 'WH: Stock → Pre-Production (MTO)' is inactive and not shown in MTO route.
        self.assertEqual(self.warehouse_1.manufacture_steps, 'mrp_one_step')
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.active)
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.location_dest_id.active)
        self.assertFalse(self.route_mto.active)
        self.assertNotIn(self.warehouse_1.pbm_mto_pull_id, self.route_mto.rule_ids)

        # Activate the MTO route and still 'WH: Stock → Pre-Production (MTO)' is not shown in MTO route.
        self.route_mto.active = True
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.active)
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.location_dest_id.active)
        self.assertNotIn(self.warehouse_1.pbm_mto_pull_id, self.route_mto.rule_ids)

        # Change MRP steps mrp_one_step to pbm_sam and now that rule is shown in mto route.
        self.warehouse_1.manufacture_steps = 'pbm_sam'
        self.assertTrue(self.warehouse_1.pbm_mto_pull_id.active)
        self.assertTrue(self.warehouse_1.pbm_mto_pull_id.location_dest_id.active)
        self.assertIn(self.warehouse_1.pbm_mto_pull_id, self.route_mto.rule_ids)

        # Revert to mrp_one_step MRP and confirm rules visibility is updated correctly
        self.warehouse_1.manufacture_steps = 'mrp_one_step'
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.active)
        self.assertFalse(self.warehouse_1.pbm_mto_pull_id.location_dest_id.active)
        self.assertNotIn(self.warehouse_1.pbm_mto_pull_id, self.route_mto.rule_ids)


class TestKitPicking(common.TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_product(name):
            p = Form(cls.env['product.product'])
            p.name = name
            p.is_storable = True
            return p.save()

        # Create a kit 'kit_parent' :
        # ---------------------------
        #
        # kit_parent --|- kit_2 x2 --|- component_d x1
        #              |             |- kit_1 x2 -------|- component_a   x2
        #              |                                |- component_b   x1
        #              |                                |- component_c   x3
        #              |
        #              |- kit_3 x1 --|- component_f x1
        #              |             |- component_g x2
        #              |
        #              |- component_e x1
        # Creating all components
        component_a = create_product('Comp A')
        component_b = create_product('Comp B')
        component_c = create_product('Comp C')
        component_d = create_product('Comp D')
        component_e = create_product('Comp E')
        component_f = create_product('Comp F')
        component_g = create_product('Comp G')
        # Creating all kits
        cls.kit_1 = create_product('Kit 1')
        cls.kit_2 = create_product('Kit 2')
        cls.kit_3 = create_product('kit 3')
        cls.kit_parent = create_product('Kit Parent')
        # Linking the kits and the components via some 'phantom' BoMs
        bom_kit_1 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})
        BomLine = cls.env['mrp.bom.line']
        BomLine.create({
            'product_id': component_a.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_1.id})
        BomLine.create({
            'product_id': component_b.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_1.id})
        BomLine.create({
            'product_id': component_c.id,
            'product_qty': 3.0,
            'bom_id': bom_kit_1.id})
        bom_kit_2 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})
        BomLine.create({
            'product_id': component_d.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_2.id})
        BomLine.create({
            'product_id': cls.kit_1.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_2.id})
        bom_kit_parent = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_parent.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})
        BomLine.create({
            'product_id': component_e.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_parent.id})
        BomLine.create({
            'product_id': cls.kit_2.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})
        bom_kit_3 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_3.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})
        BomLine.create({
            'product_id': component_f.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_3.id})
        BomLine.create({
            'product_id': component_g.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_3.id})
        BomLine.create({
            'product_id': cls.kit_3.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_parent.id})

        # We create an 'immediate transfer' receipt for x3 kit_parent
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Notthat Guyagain',
        })
        cls.test_supplier = cls.env['stock.location'].create({
            'name': 'supplier',
            'usage': 'supplier',
            'location_id': cls.stock_location.id,
        })

        cls.expected_quantities = {
            component_a: 24,
            component_b: 12,
            component_c: 36,
            component_d: 6,
            component_e: 3,
            component_f: 3,
            component_g: 6
        }

    def test_kit_immediate_transfer(self):
        """ Make sure a kit is split in the corrects quantity by components in case of an
        immediate transfer.
        """
        picking = self.env['stock.picking'].create({
            'location_id': self.test_supplier.id,
            'location_dest_id': self.warehouse_1.wh_input_stock_loc_id.id,
            'partner_id': self.test_partner.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'product_id': self.kit_parent.id,
            'quantity': 3,
            'picked': True,
            'product_uom': self.kit_parent.uom_id.id,
            'picking_id': picking.id,
            'picking_type_id': self.picking_type_in.id,
            'location_id':  self.test_supplier.id,
            'location_dest_id': self.warehouse_1.wh_input_stock_loc_id.id,
        })
        picking.button_validate()

        # We check that the picking has the correct quantities after its move were splitted.
        self.assertEqual(len(picking.move_ids), 7)
        for move in picking.move_ids:
            self.assertEqual(move.quantity, self.expected_quantities[move.product_id])
            self.assertEqual(move.state, 'done')

    def test_kit_planned_transfer(self):
        """ Make sure a kit is split in the corrects product_qty by components in case of a
        planned transfer.
        """
        picking = self.env['stock.picking'].create({
            'location_id': self.test_supplier.id,
            'location_dest_id': self.warehouse_1.wh_input_stock_loc_id.id,
            'partner_id': self.test_partner.id,
            'picking_type_id': self.picking_type_in.id,
        })
        move_receipt_1 = self.env['stock.move'].create({
            'product_id': self.kit_parent.id,
            'product_uom_qty': 3,
            'product_uom': self.kit_parent.uom_id.id,
            'picking_id': picking.id,
            'picking_type_id': self.picking_type_in.id,
            'location_id':  self.test_supplier.id,
            'location_dest_id': self.warehouse_1.wh_input_stock_loc_id.id,
        })
        picking.action_confirm()

        # We check that the picking has the correct quantities after its move were splitted.
        self.assertEqual(len(picking.move_ids), 7)
        for move_line in picking.move_ids:
            self.assertEqual(move_line.product_qty, self.expected_quantities[move_line.product_id])

    def test_add_sml_with_kit_to_confirmed_picking(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        in_type = warehouse.in_type_id

        self.bom_4.type = 'phantom'
        kit = self.bom_4.product_id
        compo = self.bom_4.bom_line_ids.product_id
        product = self.env['product.product'].create({'name': 'Super Product', 'is_storable': True})

        receipt = self.env['stock.picking'].create({
            'picking_type_id': in_type.id,
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': self.stock_location.id,
            })]
        })
        receipt.action_confirm()

        receipt.move_line_ids.quantity = 1
        receipt.move_line_ids = [Command.create({
            'product_id': kit.id,
            'quantity': 1,
            'product_uom_id': kit.uom_id.id,
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
        })]
        receipt.move_ids.picked = True

        receipt.button_validate()

        self.assertEqual(receipt.state, 'done')
        self.assertRecordValues(receipt.move_ids, [
            {'product_id': product.id, 'quantity': 1, 'state': 'done'},
            {'product_id': compo.id, 'quantity': 1, 'state': 'done'},
        ])

    def test_move_line_aggregated_product_quantities_with_kit(self):
        """ Test the `stock.move.line` method `_get_aggregated_product_quantities`,
        who returns data used to print delivery slips, using kits.
        """
        kit, kit_component_1, kit_component_2, not_kit_1, not_kit_2 = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        } for name in ['Kit', 'Kit Component 1', 'Kit Component 2', 'Not Kit 1', 'Not Kit 2']])

        bom_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_uom_id': kit.product_tmpl_id.uom_id.id,
            'product_id': kit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': kit_component_1.id,
                    'product_qty': 1,
                }),
                Command.create({
                    'product_id': kit_component_2.id,
                    'product_qty': 1,
                }),
            ]
        })

        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_in
        with delivery_form.move_ids.new() as move:
            move.product_id = bom_kit.product_id
            move.product_uom_qty = 4
        with delivery_form.move_ids.new() as move:
            move.product_id = not_kit_1
            move.product_uom_qty = 4
        with delivery_form.move_ids.new() as move:
            move.product_id = not_kit_2
            move.product_uom_qty = 3
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery.move_line_ids.filtered(lambda ml: ml.product_id == kit_component_1).quantity = 3
        delivery.move_line_ids.filtered(lambda ml: ml.product_id == kit_component_2).quantity = 3
        delivery.move_line_ids.filtered(lambda ml: ml.product_id == not_kit_1).quantity = 4
        delivery.move_line_ids.filtered(lambda ml: ml.product_id == not_kit_2).quantity = 2
        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process_cancel_backorder()

        aggregate_not_kit_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_not_kit_values.keys()), 2)
        self.assertTrue(all('Not' in val for val in aggregate_not_kit_values), 'Only non kit products should be included')

        aggregate_kit_values = delivery.move_line_ids._get_aggregated_product_quantities(kit_name=bom_kit.product_id.name)
        self.assertEqual(len(aggregate_kit_values.keys()), 2)
        self.assertTrue(all('Component' in val for val in aggregate_kit_values), 'Only kit products should be included')

    def test_scrap_consu_kit_not_available(self):
        """
        Scrap a consumable kit with one product not available in stock
        """
        self._test_scrap_kit_not_available(False)

    def test_scrap_storable_kit_not_available(self):
        """
        Scrap a storable kit with one product not available in stock
        """
        self._test_scrap_kit_not_available(True)

    def _test_scrap_kit_not_available(self, storable):
        bom = self.bom_4
        bom.type = 'phantom'

        kit = bom.product_id
        component = bom.bom_line_ids.product_id
        kit.is_storable = storable
        component.is_storable = True

        scrap = self.env['stock.scrap'].create({
            'product_id': kit.id,
            'product_uom_id': kit.uom_id.id,
            'scrap_qty': 1,
            'bom_id': bom.id,
        })

        Form.from_action(self.env, scrap.action_validate()).save().action_done()

        self.assertEqual(scrap.state, 'done')
        self.assertRecordValues(scrap.move_ids, [
            {'product_id': component.id, 'quantity': 1, 'state': 'done'}
        ])

    def test_kit_with_packaging_different_uom(self):
        """
        Test that a quantity packaging is correctly computed on a move line
        when a kit is in a different uom than its components.
        - Component(uom=Kg)
        - Kit (uom=unit) -> Bom (1 dozen) -> Component (10 g)
        - Packaging (qty=2 units of kit)
        """
        bom = self.bom_4
        bom.product_id = False
        bom.type = 'phantom'
        kit = bom.product_tmpl_id.product_variant_id
        kit.is_storable = True
        # product is in unit and bom in dozen
        kit.uom_id = self.uom_unit
        bom.product_uom_id = self.uom_dozen
        bom.product_qty = 1
        # create a packaging with 2 units
        packaging = self.env['uom.uom'].create({
            'name': 'Pack of 2',
            'relative_factor': 2,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        # component is in Kg but bom_line in gram
        component = bom.bom_line_ids.product_id
        component.uom_id = self.uom_kg
        bom.bom_line_ids.product_uom_id = self.uom_gram
        bom.bom_line_ids.product_qty = 10

        # create a delivery with 20 units of kit
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id

        delivery = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [Command.create({
                'product_id': kit.id,
                'product_uom_qty': 12,
                'product_uom': packaging.id,
                'location_id': stock_location.id,
                'location_dest_id': self.customer_location.id,
            })],
        })
        delivery.action_confirm()
        self.assertEqual(delivery.move_ids.product_id, component)
        self.assertEqual(delivery.move_ids.product_uom_qty, 20)
        delivery.move_ids.quantity = 20
        delivery.move_ids.picked = True
        delivery.button_validate()
        self.assertTrue(delivery.state, 'done')

    def test_search_kit_on_quantity(self):
        self.env['stock.quant'].create([{
            'product_id': product.id,
            'inventory_quantity': qty,
            'location_id': self.test_supplier.id,
        } for product, qty in self.expected_quantities.items()]).action_apply_inventory()

        products = self.env['product.product'].search([
            '&', ('qty_available', '>', 3), ('qty_available', '<', 9),
        ])
        self.assertNotIn(self.kit_1, products)  # 12
        self.assertIn(self.kit_2, products)     # 6
        self.assertNotIn(self.kit_3, products)  # 3

    def test_scrap_change_product(self):
        """ Ensure a scrap order automatically updates the BoM when its product is changed,
        selecting the product's first BoM if it's a kit or set the field empty otherwise."""
        bom_a = self.bom_1
        bom_a.type = 'phantom'
        product_a = bom_a.product_id

        bom_b = self.bom_3
        bom_b.type = 'phantom'
        product_b = bom_b.product_id

        product_c = self.env['product.product'].create({'name': 'product_c', 'is_storable': True})

        form = Form(self.env['stock.scrap'])
        form.product_id = product_a
        form.bom_id = bom_a
        form.scrap_qty = 1
        scrap = form.save()

        # assert the scrap's bom_id is set to bom_a
        self.assertEqual(scrap.bom_id, bom_a)

        form.product_id = product_b
        scrap = form.save()

        # assert the scrap's bom_id is set to bom_b after updating the product
        self.assertEqual(scrap.bom_id, bom_b)

        form.product_id = product_c
        scrap = form.save()

        # assert the scrap's bom_id is updated to False after updating the product
        self.assertFalse(scrap.bom_id)

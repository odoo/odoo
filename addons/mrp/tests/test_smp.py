# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form
from odoo import Command


class TestMrpSerialMassProduce(TestMrpCommon):

    def test_smp_serial(self):
        """Create a MO for a product not tracked by serial number.
        The smp wizard should not open.
        """
        mo = self.generate_mo()[0]
        self.assertEqual(mo.state, 'confirmed')
        res = mo.action_mass_produce()
        self.assertFalse(res)

    def test_smp_produce_all(self):
        """Create a MO for a product tracked by serial number.
        Open the smp wizard, generate all serial numbers to produce all quantities.
        """
        mo = self.generate_mo(tracking_final='serial')[0]
        count = mo.product_qty
        # Make some stock and reserve
        for product in mo.move_raw_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': mo.location_src_id.id,
            })._apply_inventory()
        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids.move_line_ids), 1)
        mo.qty_producing = 0
        # Open the wizard
        action = mo.action_mass_produce()
        wizard_form = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard_form.lot_name = "sn#1"
        wizard_form.lot_qty = count
        wizard = wizard_form.save()
        wizard.action_generate_production_text()
        wizard.action_prepare()
        # Initial MO should have a backorder-sequenced name and be in progress state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "progress")
        # Each generated serial number should have its own mo
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), count)
        # Check generated serial numbers
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.lot_producing_id.mapped('name'), ["sn#1", "sn#2", "sn#3", "sn#4", "sn#5"])

    def test_smp_produce_all_but_one(self):
        """Create a MO for a product tracked by serial number.
        Open the smp wizard, generate all but one serial numbers and create a back order.
        """
        mo = self.generate_mo(tracking_final='serial')[0]
        count = mo.product_qty
        # Make some stock and reserve
        for product in mo.move_raw_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': mo.location_src_id.id,
            })._apply_inventory()
        mo.action_assign()
        action = mo.action_mass_produce()
        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        wizard.lot_name = "sn#1"
        wizard.lot_qty = count - 1
        wizard = wizard.save()
        wizard.action_generate_production_text()
        wizard.action_prepare()

        # Last MO in sequence is the backorder
        bo = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(bo.backorder_sequence, count)
        self.assertEqual(bo.state, "confirmed")

    def test_smp_produce_complex(self):
        """Create a MO for a product tracked by serial number
        and with complex components (serial and multiple lots).
        Open the smp wizard, generate all serial numbers to produce all quantities.
        Check lot splitting.
        """
        mo, dummy, dummy, product_to_use_1, product_to_use_2 = self.generate_mo(tracking_final='serial', tracking_base_1='lot', tracking_base_2='serial', qty_final=3, qty_base_1=2, qty_base_2=1)
        count = mo.product_qty
        # Make some stock and reserve
        for _ in range(2):  # 2 lots of 3 to satisfy the need and check lot splitting
            lot = self.env['stock.lot'].create({
                'product_id': product_to_use_1.id,
            })
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_to_use_1.id,
                'inventory_quantity': 3,
                'location_id': mo.location_src_id.id,
                'lot_id': lot.id,
            })._apply_inventory()
        for _ in range(3):  # 3 serial numbers
            lot = self.env['stock.lot'].create({
                'product_id': product_to_use_2.id,
            })
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_to_use_2.id,
                'inventory_quantity': 1,
                'location_id': mo.location_src_id.id,
                'lot_id': lot.id,
            })._apply_inventory()
        mo.action_assign()
        # Open the wizard
        action = mo.action_mass_produce()
        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.lot_name = "sn#1"
        wizard.lot_qty = count
        wizard = wizard.save()
        wizard.action_generate_production_text()
        wizard.action_prepare()
        # 1st & 2nd MO in sequence should have only 1 move lines (1 lot) for product_to_use_1 (2nd in bom)
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[0].move_raw_ids[1].move_lines_count, 1)
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[1].move_raw_ids[1].move_lines_count, 1)
        # 3rd MO should have 2 move lines (2 different lots) for product_to_use_1
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[2].move_raw_ids[1].move_lines_count, 2)

        # Verify mark as done

        mos = mo.procurement_group_id.mrp_production_ids
        mos.button_mark_done()

        self.assertRecordValues(mos.lot_producing_id, [
            {'product_qty': 1},
            {'product_qty': 1},
            {'product_qty': 1},
        ])

        self.assertRecordValues(mos.move_finished_ids, [
            {'picked': True},
            {'picked': True},
            {'picked': True},
        ])

        self.assertRecordValues(mos.move_raw_ids, [
            {'picked': True},
            {'picked': True},
            {'picked': True},
            {'picked': True},
            {'picked': True},
            {'picked': True},
        ])

    def test_mass_produce_with_tracked_product(self):
        """
        Check that we can mass produce a tracked product.
        """
        tracked_product = self.env['product.product'].create({
            'name': 'Tracked Product',
            'is_storable': True,
            'tracking': 'serial',
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
        })
        byproduct = self.env['product.product'].create({
            'name': 'Byproduct',
            'is_storable': True,
        })
        # create a BoM
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': tracked_product.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [Command.create({
                'product_id': component.id,
                'product_qty': 1,
            })],
            'byproduct_ids': [Command.create({
                'product_id': byproduct.id,
                'product_qty': 1,
            })],
        })
        sn_1 = self.env['stock.lot'].create({
            'name': 'SN1',
            'product_id': tracked_product.id,
        })
        sn_2 = self.env['stock.lot'].create({
            'name': 'SN2',
            'product_id': tracked_product.id,
        })
        self.env['stock.quant']._update_available_quantity(tracked_product, self.shelf_1, 1, lot_id=sn_1)
        self.env['stock.quant']._update_available_quantity(tracked_product, self.shelf_1, 1, lot_id=sn_2)
        self.env['stock.quant']._update_available_quantity(component, self.shelf_1, 10)
        # create an MO to use the tracked product available in stock
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.product_qty = 2
        mo_form.product_uom_id = component.uom_id
        # use tracked  as component
        with mo_form.move_raw_ids.new() as move:
            move.product_id = tracked_product
            move.product_uom_qty = 2
            move.product_uom = tracked_product.uom_id
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.qty_producing = 2
        mo.move_raw_ids.move_line_ids.write({'quantity': 1})
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        # create a Mo to produce 2 units of tracked product
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = tracked_product
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo_form.product_uom_id = tracked_product.uom_id
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')

        mo.action_assign()
        # Open the wizard
        action = mo.action_mass_produce()

        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.lot_name = "sn#3"
        wizard.lot_qty = 2
        wizard = wizard.save()
        wizard.action_generate_production_text()
        # Reload the wizard to apply generated serial numbers
        wizard.action_prepare()
        # Initial MO should have a backorder-sequenced name and be in confirmed state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "confirmed")
        # Each generated serial number should have its own mo
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        # Check generated serial numbers
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.lot_producing_id.mapped('name'), ["sn#3", "sn#4"])
        #check byproduct quantity
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.move_byproduct_ids.mapped('quantity'), [1, 1])
        # check the component quantity
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.move_raw_ids.mapped('quantity'), [1, 1])
        # Mark the MOs as done
        mo.procurement_group_id.mrp_production_ids.move_raw_ids.picked = True
        mo.procurement_group_id.mrp_production_ids.button_mark_done()
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.mapped('state'), ['done', 'done'])

    def test_mass_produce_with_tracked_product_2(self):
        """
        Check that the components are correclty consumed during mass
        production of a tracked product.
        """
        mo = self.generate_mo(tracking_final='serial', qty_final=3, qty_base_1=1, qty_base_2=1)[0]
        comp1, comp2 = mo.move_raw_ids.mapped('product_id')
        self.env['stock.quant']._update_available_quantity(comp1, mo.warehouse_id.lot_stock_id, 5)
        # Generate an SN using the action_generate_serial
        mo.action_generate_serial()
        # In the end mass produce the SN's
        action = mo.action_mass_produce()
        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.lot_name = "sn#5"
        wizard.lot_qty = 3
        wizard = wizard.save()
        wizard.action_generate_production_text()
        # Reload the wizard to apply generated serial numbers
        wizard.action_prepare()

        # Initial MO should have a backorder-sequenced name and be in to_close state
        self.assertIn("-001", mo.name)
        self.assertEqual(mo.state, "to_close")
        # Each generated serial number should have its own mo
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.lot_producing_id.mapped('name'), ["sn#5", "sn#6", "sn#7"])
        # check the component quantity
        self.assertRecordValues(mo.procurement_group_id.mrp_production_ids.move_raw_ids, [
            {'quantity': 1.0, 'picked': True},
            {'quantity': 1.0, 'picked': True},
            {'quantity': 1.0, 'picked': False},
            {'quantity': 0.0, 'picked': False},
            {'quantity': 1.0, 'picked': False},
            {'quantity': 0.0, 'picked': False},
        ])
        mo.procurement_group_id.mrp_production_ids.button_mark_done()
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.mapped('state'), ['done', 'done', 'done'])
        self.assertEqual(comp1.qty_available, 2.0)
        self.assertEqual(comp2.qty_available, -3.0)

    def test_smp_produce_with_consumable_component(self):
        """Create a MO for a product tracked by serial number with a consumable component.
        Open the smp wizard, You should be able to generate all serial numbers.
        BoM:
        - 1x final product (tracked by serial number)
        components:
        - 2 x (storable)
        - 4 x (consumable)
        - Create a MO with 12 final products to produce.
        - update the component quantity to 100
        """
        self.bom_1.product_uom_id = self.bom_1.product_id.uom_id
        self.bom_1.product_id.uom_id = self.ref('uom.product_uom_unit')
        self.bom_1.product_id.tracking = 'serial'
        self.bom_1.product_qty = 1

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 12
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.mapped(lambda l: l.product_qty), [24, 48])
        self.assertEqual(mo.move_raw_ids[1].product_id.type, 'consu', 'The second component should be consumable')
        mo.move_raw_ids[1].product_uom_qty = 100

        # Make some stock and reserve for storable component
        self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': mo.move_raw_ids[0].product_id.id,
                'inventory_quantity': 24,
                'location_id': mo.location_src_id.id,
        })._apply_inventory()

        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')

        # Open the wizard
        action = mo.button_mark_done()
        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.lot_name = "sn#1"
        wizard.lot_qty = mo.product_qty
        wizard = wizard.save()
        wizard.action_generate_production_text()
        wizard.action_prepare()

        # Initial MO should have a backorder-sequenced name and be in confirmed state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "confirmed")
        # Each generated serial number should have its own mo
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 12)

    def test_smp_two_steps(self):
        """Create a MO for a product tracked by lot and with a component untracked and tracked by lot.
           As the smp wizard should not open even if in two steps
        """
        self.env['res.config.settings'].write({
            'group_stock_adv_location': True,
        })
        self.warehouse_1.manufacture_steps = 'pbm'
        mo = self.generate_mo(tracking_final='lot', tracking_base_1='lot')[0]
        # Make some stock and reserve
        for product in mo.move_raw_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': mo.location_src_id.id,
            })._apply_inventory()
        mo.action_assign()
        action = mo.action_mass_produce()
        self.assertEqual(action, None)

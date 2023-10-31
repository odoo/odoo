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
        res = mo.action_serial_mass_produce_wizard()
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
        # Open the wizard
        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.next_serial_number = "sn#1"
        wizard.next_serial_count = count
        action = wizard.save().generate_serial_numbers_production()
        # Reload the wizard to apply generated serial numbers
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard.save().apply()
        # Initial MO should have a backorder-sequenced name and be in to_close state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "to_close")
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
        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        wizard.next_serial_number = "sn#1"
        wizard.next_serial_count = count - 1
        action = wizard.save().generate_serial_numbers_production()
        # Reload the wizard to create backorder (applying generated serial numbers)
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard.save().create_backorder()
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
                'company_id': self.env.company.id,
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
                'company_id': self.env.company.id,
            })
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_to_use_2.id,
                'inventory_quantity': 1,
                'location_id': mo.location_src_id.id,
                'lot_id': lot.id,
            })._apply_inventory()
        mo.action_assign()
        # Open the wizard
        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.next_serial_number = "sn#1"
        wizard.next_serial_count = count
        action = wizard.save().generate_serial_numbers_production()
        # Reload the wizard to apply generated serial numbers
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard.save().apply()
        # 1st & 2nd MO in sequence should have only 1 move lines (1 lot) for product_to_use_1 (2nd in bom)
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[0].move_raw_ids[1].move_lines_count, 1)
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[1].move_raw_ids[1].move_lines_count, 1)
        # 3rd MO should have 2 move lines (2 different lots) for product_to_use_1
        self.assertEqual(mo.procurement_group_id.mrp_production_ids[2].move_raw_ids[1].move_lines_count, 2)

        # Verify if lot IDs were correctly assigned to move lines
        mo.procurement_group_id.mrp_production_ids.button_mark_done()

        final_sns = mo.procurement_group_id.mrp_production_ids.lot_producing_id
        self.assertRecordValues(final_sns, [
            {'product_qty': 1},
            {'product_qty': 1},
            {'product_qty': 1},
        ])

    def test_mass_produce_with_tracked_product(self):
        """
        Check that we can mass produce a tracked product.
        """
        tracked_product = self.env['product.product'].create({
            'name': 'Tracked Product',
            'type': 'product',
            'tracking': 'serial',
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
        })
        byproduct = self.env['product.product'].create({
            'name': 'Byproduct',
            'type': 'product',
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
        self.env['stock.quant']._update_available_quantity(tracked_product, self.stock_location_14, 1, lot_id=sn_1)
        self.env['stock.quant']._update_available_quantity(tracked_product, self.stock_location_14, 1, lot_id=sn_2)
        self.env['stock.quant']._update_available_quantity(component, self.stock_location_14, 10)
        # create an MO to use the tracked product available in stock
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.product_qty = 2
        mo_form.product_uom_id = component.uom_id
        # use tracked  as component
        with mo_form.move_raw_ids.new() as move:
            move.name = tracked_product.name
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
        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        # Let the wizard generate all serial numbers
        wizard.next_serial_number = "sn#3"
        wizard.next_serial_count = 2
        action = wizard.save().generate_serial_numbers_production()
        # Reload the wizard to apply generated serial numbers
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard.save().apply()
        # Initial MO should have a backorder-sequenced name and be in to_close state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "to_close")
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

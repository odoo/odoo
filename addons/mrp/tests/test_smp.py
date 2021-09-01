# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form
from odoo.exceptions import UserError

class TestMrpSerialMassProduce(TestMrpCommon):

    def test_smp_serial(self):
        """Create a MO for a product not tracked by serial number.
        The smp wizard should not open.
        """
        mo = self.generate_mo()[0]
        self.assertEqual(mo.state, 'confirmed')
        res = mo.action_serial_mass_produce_wizard()
        self.assertFalse(res)

    def test_smp_no_serial_component(self):
        """Create a MO for a product tracked by serial number with a component also tracked by serial number.
        An error should be throwed.
        """
        mo = self.generate_mo(tracking_final='serial', tracking_base_2='serial')[0]
        with self.assertRaises(UserError):
            mo.action_serial_mass_produce_wizard()

    def test_smp_produce_all(self):
        """Create a MO for a product tracked by serial number.
        Open the smp wizard, generate all serial numbers to produce all quantitites.
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

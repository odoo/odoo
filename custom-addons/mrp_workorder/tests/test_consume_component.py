# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.mrp.tests.test_consume_component import TestConsumeComponentCommon

@tagged('post_install', '-at_install')
class TestConsumeTrackedComponent(TestConsumeComponentCommon):

    @classmethod
    def setUpClass(cls):
        super(TestConsumeTrackedComponent, cls).setUpClass()

        cls.consume_quality_point = cls.env.ref('mrp_workorder.test_type_register_consumed_materials')

        cls.routing_workcenter_serial = cls.env['mrp.routing.workcenter'].create({
            'bom_id': cls.bom_serial.id,
            'workcenter_id': cls.workcenter.id,
            'time_cycle': 120,
            'sequence': 1,
            'name': 'Assembly'
        })

        cls.bom_serial_line_serial = list(filter(lambda boml: boml.tracking == 'serial', cls.bom_serial.bom_line_ids))[0]
        cls.bom_serial_line_serial.operation_id = cls.routing_workcenter_serial

        cls.quality_point = cls.env['quality.point'].create({
            'product_ids': [(4, cls.produced_serial.id)],
            'operation_id': cls.routing_workcenter_serial.id,
            'test_type_id': cls.consume_quality_point.id,
            'component_id': cls.raw_serial.id,
            'sequence': 1,
            'note': 'Please enter the Raw Serial serial number',
            'title': 'Component Registration : Raw Serial',
            'picking_type_ids': [(4, cls.picking_type.id)],
        })

    def test_option_enabled_and_operation_id_and_quality_point(self):
        """
        Auto-consume is enabled
        There's a BoM.operation_id and a quality_point on the 'serial' component
        -> Consumption step already exist
        -> No auto-consumption of the 'serial' component
        -> Auto-consumption of other components
        """
        self.assertTrue(self.picking_type.use_auto_consume_components_lots)
        # Create manufacturing order
        mo_serial = self.create_mo(self.mo_serial_tmpl, 1)
        mo_serial.action_confirm()

        self.assertTrue(self.raw_serial in mo_serial.workorder_ids.quality_point_ids.component_id)
        self.assertTrue(self.routing_workcenter_serial in mo_serial.move_raw_ids.operation_id)

        quant = self.create_quant(self.raw_none, 3)
        quant |= self.create_quant(self.raw_lot, 2)
        quant |= self.create_quant(self.raw_serial, 1)
        quant.action_apply_inventory()

        # Quantities are fully reserved (stock.move state is available)
        mo_serial.action_assign()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Reserved quantity shall be equal to To Consume quantity.")

        mo_serial.action_generate_serial()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_and_operation_id(self):
        """
        Auto-consume is enabled
        There's a BoM.operation_id on the 'serial' component
        -> Consumption step is created
        -> No auto-consumption of the 'serial' component
        -> Auto-consumption of other components
        """
        self.assertTrue(self.picking_type.use_auto_consume_components_lots)

        self.quality_point.active = False

        # Create manufacturing order
        mo_serial = self.create_mo(self.mo_serial_tmpl, 1)
        mo_serial.action_confirm()

        self.assertFalse(self.raw_serial in mo_serial.workorder_ids.quality_point_ids.component_id)
        self.assertTrue(self.routing_workcenter_serial in mo_serial.move_raw_ids.operation_id)

        quant = self.create_quant(self.raw_none, 3)
        quant |= self.create_quant(self.raw_lot, 2)
        quant |= self.create_quant(self.raw_serial, 1)
        quant.action_apply_inventory()

        # Quantities are fully reserved (stock.move state is available)
        mo_serial.action_assign()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Reserved quantity shall be equal to To Consume quantity.")

        mo_serial.action_generate_serial()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_and_quality_point(self):
        """
        Auto-consume is enabled
        There's a quality_point on the 'serial' component
        -> Consumption step already exist
        -> No auto-consumption of the 'serial' component
        -> Auto-consumption of other components
        """
        self.assertTrue(self.picking_type.use_auto_consume_components_lots)

        self.quality_point.active = True
        self.bom_serial_line_serial.operation_id = self.env['mrp.routing.workcenter']

        # Create manufacturing order
        mo_serial = self.create_mo(self.mo_serial_tmpl, 1)
        mo_serial.action_confirm()

        self.assertTrue(self.raw_serial in mo_serial.workorder_ids.quality_point_ids.component_id)
        self.assertFalse(self.routing_workcenter_serial in mo_serial.move_raw_ids.operation_id)

        quant = self.create_quant(self.raw_none, 3)
        quant |= self.create_quant(self.raw_lot, 2)
        quant |= self.create_quant(self.raw_serial, 1)
        quant.action_apply_inventory()

        # Quantities are fully reserved (stock.move state is available)
        mo_serial.action_assign()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Reserved quantity shall be equal to To Consume quantity.")

        mo_serial.action_generate_serial()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_only(self):
        """
        Auto-consume is enabled
        There's neither a BoM.operation_id nor a quality_point on the 'serial' component
        -> No Consumption step
        -> Auto-consumption of all components
        """
        self.assertTrue(self.picking_type.use_auto_consume_components_lots)

        self.quality_point.active = False
        self.bom_serial_line_serial.operation_id = self.env['mrp.routing.workcenter']

        # Create manufacturing order
        mo_serial = self.create_mo(self.mo_serial_tmpl, 1)
        mo_serial.action_confirm()

        self.assertFalse(self.raw_serial in mo_serial.workorder_ids.quality_point_ids.component_id)
        self.assertFalse(self.routing_workcenter_serial in mo_serial.move_raw_ids.operation_id)

        quant = self.create_quant(self.raw_none, 3)
        quant |= self.create_quant(self.raw_lot, 2)
        quant |= self.create_quant(self.raw_serial, 1)
        quant.action_apply_inventory()

        # Quantities are fully reserved (stock.move state is available)
        mo_serial.action_assign()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Reserved quantity shall be equal to To Consume quantity.")

        mo_serial.action_generate_serial()
        for mov in mo_serial.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")

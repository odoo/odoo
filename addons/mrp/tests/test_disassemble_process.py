# -*- coding: utf-8 -*-

from openerp.tools import float_compare
from openerp.tests.common import TransactionCase


class TestDisassembleProcess(TransactionCase):

    """ Test used to check that when doing disassemble process."""

    def setUp(self):
        super(TestDisassembleProcess, self).setUp()
        # Create a user as 'MRP User'
        self.mrp = self.env['mrp.production']
        group_mrp_user = self.env.ref('mrp.group_mrp_user')
        self.mrpuser = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'MRP User',
            'login': 'mau',
            'password': 'mau',
            'email': 'mrp_user@yourcompany.com',
            'groups_id': [(6, 0, [group_mrp_user.id])]
        })

        self.mrp_production = self.env['mrp.production']
        self.product4 = self.env.ref('product.product_product_4')
        self.stock_location_14 = self.env.ref('stock.stock_location_14')
        self.location_output = self.env.ref('stock.stock_location_output')
        self.mrp_bom_9 = self.env.ref('mrp.mrp_bom_9')
        self.mrp_routing_1 = self.env.ref('mrp.mrp_routing_1')

    def test_disassemble_process(self):
        "MRP user can doing all process related to Production Order"
        "In order to test Disassemble feature in OpenERP we will create a Production order with negative quantity for PC Assemble SC349"

        mrp_production_test2 = self.mrp_production.sudo(self.mrpuser.id).create({
            'product_id': self.product4.id,
            'product_qty': -5.0,
            'location_src_id': self.stock_location_14.id,
            'location_dest_id': self.location_output.id,
            'bom_id': self.mrp_bom_9.id,
            'routing_id': self.mrp_routing_1.id
        })

        # I compute the production order.
        mrp_production_test2.action_compute()

        # I check production lines after compute.
        self.assertEqual(len(mrp_production_test2.product_lines), 5, "Production lines are not generated proper.")

        # Now I check workcenter lines.

        def assert_equals(value1, value2, msg, float_compare=float_compare):
            assert float_compare(value1, value2, precision_digits=2) == 0, msg

        assert len(mrp_production_test2.workcenter_lines), "Workcenter lines are not generated proper."

        # I confirm the Production Order.
        mrp_production_test2.signal_workflow('moves_ready_disassemble')

        # I check details of Produce Move of Production Order to trace Final Product.
        assert mrp_production_test2.state == 'ready', "Production order should be ready."
        assert mrp_production_test2.move_created_ids, "Trace Record is not created for Final Product."
        move = mrp_production_test2.move_created_ids[0]
        source_location_id = mrp_production_test2.product_id.property_stock_production.id
        assert move.date == mrp_production_test2.date_planned, "Planned date is not correspond."
        assert move.product_id.id == mrp_production_test2.product_id.id, "Product is not correspond."
        assert move.product_uom.id == mrp_production_test2.product_uom.id, "UOM is not correspond."
        assert move.product_qty == abs(mrp_production_test2.product_qty), "Qty is not correspond."
        assert move.product_uos_qty == mrp_production_test2.product_uos and mrp_production_test2.product_uos_qty or abs(mrp_production_test2.product_qty), "UOS qty is not correspond."
        if mrp_production_test2.product_uos:
            assert move.product_uos.id == mrp_production_test2.product_uos.id, "UOS is not correspond."
        assert move.location_id.id == source_location_id, "Source Location is not correspond."
        assert move.location_dest_id.id == mrp_production_test2.location_dest_id.id, "Destination Location is not correspond."
        routing_loc = None
        if mrp_production_test2.bom_id.routing_id and mrp_production_test2.bom_id.routing_id.location_id:
            routing_loc = mrp_production_test2.bom_id.routing_id.location_id.id
        date_planned = mrp_production_test2.date_planned
        for move_line in mrp_production_test2.move_lines:
            for order_line in mrp_production_test2.product_lines:
                if move_line.product_id.type not in ('product', 'consu'):
                    continue
                if move_line.product_id.id == order_line.product_id.id:
                    assert move_line.date == date_planned, "Planned date is not correspond in 'To consume line'."
                    assert move_line.product_qty == order_line.product_qty, "Qty is not correspond in 'To consume line'."
                    assert move_line.product_uom.id == order_line.product_uom.id, "UOM is not correspond in 'To consume line'."
                    assert move_line.product_uos_qty == order_line.product_uos and order_line.product_uos_qty or order_line.product_qty, "UOS qty is not correspond in 'To consume line'."
                    if order_line.product_uos:
                        assert move_line.product_uos.id == order_line.product_uos.id, "UOS is not correspond in 'To consume line'."
                    assert move_line.location_id.id == source_location_id, "Source location is not correspond in 'To consume line'."
                    assert move_line.location_dest_id.id == routing_loc or mrp_production_test2.location_src_id.id, "Destination Location is not correspond in 'To consume line'."

        # I check that production order in ready state.
        assert mrp_production_test2.state == 'ready', 'Production order should be in Ready State.'

        # I check that production order in production state after start production.
        assert self.mrp.with_context(active_id=mrp_production_test2.id).action_produce(mrp_production_test2.id, 5.0, 'consume_produce'), 'Can not do action produce.'

        # I check that production order in Done state.
        assert mrp_production_test2.state == 'done', 'Production order should be in Done State.'

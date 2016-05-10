# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mrp.tests.test_order_demo import TestOrderDemo


class TestOrderProcess(TestOrderDemo):

    def test_00_order_process(self):

    # Now I check workcenter lines.
        from openerp.tools import float_compare

        def assert_equals(value1, value2, msg, float_compare=float_compare):
            assert float_compare(value1, value2, precision_digits=2) == 0, msg
        #self.assertTrue(len(self.mrp_production_test1.workorder_ids), "Workcenter lines are not generated proper.")


   # I check details of Produce Move of Production Order to trace Final Product.

        self.assertEqual(self.mrp_production_test1.state, 'confirmed', "Production order should be confirmed.")
        self.assertTrue(self.mrp_production_test1.move_finished_ids, "Trace Record is not created for Final Product.")
        move = self.mrp_production_test1.move_finished_ids[0]
        source_location_id = self.mrp_production_test1.product_id.property_stock_production.id
        self.assertEqual(move.date, self.mrp_production_test1.date_planned, "Planned date is not correspond.")
        self.assertEqual(move.product_id.id, self.mrp_production_test1.product_id.id, "Product does not correspond.")
        self.assertEqual(move.product_uom.id, self.mrp_production_test1.product_uom_id.id, "UOM does not correspond.")
        self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty does not correspond.")
        self.assertEqual(move.location_id.id, source_location_id, "Source Location does not correspond.")
        self.assertEqual(move.location_dest_id.id, self.mrp_production_test1.location_dest_id.id, "Destination Location does not correspond.")
        routing_loc = None
        if self.mrp_production_test1.bom_id.routing_id and self.mrp_production_test1.bom_id.routing_id.location_id:
            routing_loc = self.mrp_production_test1.routing_id.location_id.id
        date_planned = self.mrp_production_test1.date_planned
        for move_line in self.mrp_production_test1.move_raw_ids:
                self.assertEqual(move_line.date, date_planned, "Planned date does not correspond in 'To consume line'.")
    # I consume raw materials and put one material in scrap location due to waste it.
        scrap_location_ids = self.env['stock.location'].search([('scrap_location', '=', True)])
        scrap_location_id = scrap_location_ids[0]
        for move in self.mrp_production_test1.move_raw_ids:
            if move.product_id.id == self.env.ref("product.product_product_6").id:
                move.action_scrap(5.0, scrap_location_id)

    #I check procurements have been generated for every consume line

        # order = self.env["mrp.production"].browse(self.env.ref("mrp_production_test1"))
        move_line_ids = [x.id for x in self.mrp_production_test1.move_raw_ids]
        procurements = self.env['procurement.order'].search([('move_dest_id', 'in', move_line_ids)])
        for proc in self.env['procurement.order'].browse(procurements):
            date_planned = self.mrp_production_test1.date_planned
            if proc.product_id.type not in ('product', 'consu'):
                continue
            if proc.product_id.id == order_line.product_id.id:
                self.assertEqual(proc.date_planned, date_planned, "Planned date does not correspond")
              # procurement state should be `confirmed` at this stage, except if procurement_jit is installed, in which
              # case it could already be in `running` or `exception` state (not enough stock)
                expected_states = ('confirmed', 'running', 'exception')
                self.assertEqual(proc.state in expected_states, 'Procurement state is `%s` for %s, expected one of %s' % (proc.state, proc.product_id.name, expected_states))

        # I change production qty with 3 PC Assemble SC349.
        ctx = dict(self.env.context)
        ctx.update({'active_id': self.mrp_production_test1.id})


        #TODO: fix change production qty
        #self.mrp_production_qty = self.env['change.production.qty'].with_context(ctx).create({
        #    'product_qty': 3.0
        #})

        #self.mrp_production_qty.change_prod_qty()

        # I check qty after changed in production order.
        #self.assertEqual(self.mrp_production_test1.product_qty, 3, "Qty is not changed in order.")
        move = self.mrp_production_test1.move_finished_ids[0]
        self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty is not changed in move line.")

        # I run scheduler.
        self.env['procurement.order'].run_scheduler()

        # The production order is Waiting Goods, will force production which should set consume lines as available
        self.mrp_production_test1.button_plan()
        # I check that production order in ready state after forcing production.

        #self.assertEqual(self.mrp_production_test1.availability, 'assigned', 'Production order availability should be set as available')


    # I produce product.
        ctx.update({'active_id': self.mrp_production_test1.id})

        self.mrp_product_produce1 = self.env['mrp.product.produce'].with_context(ctx).create({})

        qty = self.mrp_product_produce1.product_qty
        self.mrp_product_produce1.do_produce()

    # I check production order after produced.
        self.assertEqual(self.mrp_production_test1.state, 'planned', "Production order should be in planned state.")

        def rounding(f, r):
            import math
            if not r:
                return f
            return math.ceil(f / r) * r


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestOrderProcess(common.TransactionCase):

    def test_00_order_process(self):
        self.res_users_mrp_manager = self.env.ref('mrp.group_mrp_manager')
        self.group_account_user = self.env.ref('account.group_account_user')
        self.main_company = self.env.ref('base.main_company')
        self.group_mrp_user = self.env.ref('mrp.group_mrp_user')

        self.res_users_mrp_manager = self.env['res.users'].create({
            'company_id': self.main_company.id,
            'name': 'MRP Manager',
            'login': 'mam',
            'password': 'mam',
            'email': 'mrp_manager@yourcompany.com',
            'groups_id': [(6, 0, [self.res_users_mrp_manager.id, self.group_account_user.id])]
        })

        # Create a user as 'MRP User'
        # I added groups for MRP User.
        self.res_users_mrp_user = self.env['res.users'].create({
            'company_id': self.main_company.id,
            'name': 'MRP User',
            'login': 'mau',
            'password': 'mau',
            'email': 'mrp_user@yourcompany.com',
            'groups_id': [(6, 0, [self.group_mrp_user.id])]
        })

        self.mrp_production_test1 = self.env['mrp.production'].sudo(self.res_users_mrp_user.id).create({
            'product_id': self.env.ref('product.product_product_3').id,
            'product_qty': 5.0,
            'location_src_id': self.env.ref('stock.stock_location_14').id,
            'location_dest_id': self.env.ref('stock.stock_location_output').id,
            'bom_id': self.env.ref('mrp.mrp_bom_kit').id,
            'routing_id': self.env.ref('mrp.mrp_routing_1').id
        })

        # I compute the production order.
        self.mrp_production_test1.action_compute()

        # I check production lines after compute.
        self.assertEqual(len(self.mrp_production_test1.product_lines), 7)

        # Now I check workcenter lines.
        from openerp.tools import float_compare

        def assert_equals(value1, value2, msg, float_compare=float_compare):
            assert float_compare(value1, value2, precision_digits=2) == 0, msg
        self.assertTrue(len(self.mrp_production_test1.workcenter_lines))

        # I confirm the Production Order.
        self.mrp_production_test1.signal_workflow('button_confirm')


        # I check details of Produce Move of Production Order to trace Final Product.

        self.assertEqual(self.mrp_production_test1.state, 'confirmed', "Production order should be confirmed.")
        self.assertTrue(self.mrp_production_test1.move_created_ids, "Trace Record is not created for Final Product.")
        move = self.mrp_production_test1.move_created_ids[0]
        source_location_id = self.mrp_production_test1.product_id.property_stock_production.id
        self.assertEqual(move.date, self.mrp_production_test1.date_planned, "Planned date is not correspond.")
        self.assertEqual(move.product_id.id, self.mrp_production_test1.product_id.id, "Product does not correspond.")
        self.assertEqual(move.product_uom.id, self.mrp_production_test1.product_uom.id, "UOM does not correspond.")
        self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty does not correspond.")
        self.assertEqual(move.location_id.id, source_location_id, "Source Location does not correspond.")
        self.assertEqual(move.location_dest_id.id, self.mrp_production_test1.location_dest_id.id, "Destination Location does not correspond.")
        routing_loc = None
        if self.mrp_production_test1.bom_id.routing_id and self.mrp_production_test1.bom_id.routing_id.location_id:
            routing_loc = self.mrp_production_test1.routing_id.location_id.id
        date_planned = self.mrp_production_test1.date_planned
        for move_line in self.mrp_production_test1.move_lines:
            for order_line in self.mrp_production_test1.product_lines:
                if move_line.product_id.type not in ('product', 'consu'):
                    continue
                if move_line.product_id.id == order_line.product_id.id:
                    self.assertEqual(move_line.date, date_planned, "Planned date does not correspond in 'To consume line'.")
                    self.assertEqual(move_line.product_qty, order_line.product_qty, "Qty does not correspond in 'To consume line'.")
                    self.assertEqual(move_line.product_uom.id, order_line.product_uom.id, "UOM does not correspond in 'To consume line'.")
                    self.assertEqual(move_line.location_id.id, routing_loc or self.mrp_production_test1.location_src_id.id, "Source location is not correspond in 'To consume line'.")
                    self.assertEqual(move_line.location_dest_id.id, source_location_id, "Destination Location is not correspond in 'To consume line'.")

        # I consume raw materials and put one material in scrap location due to waste it.
        scrap_location_ids = self.env['stock.location'].search([('scrap_location', '=', True)])
        scrap_location_id = scrap_location_ids[0]
        for move in self.mrp_production_test1.move_lines:
            if move.product_id.id == self.env.ref("product.product_product_6").id:
                move.action_scrap(5.0, scrap_location_id)

        # I check procurements have been generated for every consume line

        # order = self.env["mrp.production"].browse(self.env.ref("mrp_production_test1"))
        move_line_ids = [x.id for x in self.mrp_production_test1.move_lines]
        procurements = self.env['procurement.order'].search([('move_dest_id', 'in', move_line_ids)])
        for proc in self.env['procurement.order'].browse(procurements):
            for order_line in self.mrp_production_test1.product_lines:
                date_planned = self.mrp_production_test1.date_planned
                if proc.product_id.type not in ('product', 'consu'):
                    continue
                if proc.product_id.id == order_line.product_id.id:
                    self.assertEqual(proc.date_planned, date_planned, "Planned date does not correspond")
                    self.assertEqual(proc.product_qty, order_line.product_qty, "Qty does not correspond")
                    self.assertEqual(proc.location_id.id, self.mrp_production_test1.location_src_id.id, "Input location and procurement location do not correspond")
                    self.assertEqual(proc.product_uom_id.id, order_line.product_uom.id, "UOM does not correspond in procurement.")
                  # procurement state should be `confirmed` at this stage, except if procurement_jit is installed, in which
                  # case it could already be in `running` or `exception` state (not enough stock)
                    expected_states = ('confirmed', 'running', 'exception')
                    self.assertEqual(proc.state in expected_states, 'Procurement state is `%s` for %s, expected one of %s' % (proc.state, proc.product_id.name, expected_states))

        # I change production qty with 3 PC Assemble SC349.
        ctx = dict(self.env.context)
        ctx.update({'active_id': self.mrp_production_test1.id})

        self.mrp_production_qty = self.env['change.production.qty'].with_context(ctx).create({
            'product_qty': 3.0
        })

        self.mrp_production_qty.change_prod_qty()

        # I check qty after changed in production order.
        self.assertEqual(self.mrp_production_test1.product_qty, 3, "Qty is not changed in order.")
        move = self.mrp_production_test1.move_created_ids[0]
        self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty is not changed in move line.")

        # I run scheduler.
        self.env['procurement.order'].run_scheduler()

        # The production order is Waiting Goods, will force production which should set consume lines as available
        self.mrp_production_test1.force_production()

        # I check that production order in ready state after forcing production.

        self.assertEqual(self.mrp_production_test1.state, 'ready', 'Production order should be in Ready State.')

        # Now I start production.
        self.mrp_production_test1.signal_workflow('button_produce')

        # I check that production order in production state after start production.
        self.assertEqual(self.mrp_production_test1.state, 'in_production', 'Production order should be in production State.')

        # I produce product.
        ctx.update({'active_id': self.mrp_production_test1.id})

        self.mrp_product_produce1 = self.env['mrp.product.produce'].with_context(ctx).create({
            'mode': 'consume_produce'
        })

        qty = self.mrp_product_produce1.product_qty
        self.mrp_product_produce1.on_change_qty()
        self.mrp_product_produce1.do_produce()

        # I check production order after produced.
        self.assertEqual(self.mrp_production_test1.state, 'done', "Production order should be closed.")

        # I check Total Costs at End of Production as a manager.
        account_analytic_line = self.env['account.analytic.line']

        def rounding(f, r):
            import math
            if not r:
                return f
            return math.ceil(f / r) * r

        for workcenter_line in self.mrp_production_test1.workcenter_lines:
            workcenter = workcenter_line.workcenter_id
            accounts = [workcenter.costs_hour_account_id, workcenter.costs_cycle_account_id]
            cost_per_cyle = workcenter_line.cycle * workcenter.costs_cycle
            cost_per_hours = workcenter_line.hour * workcenter.costs_hour
            if accounts and workcenter.costs_general_account_id and (cost_per_cyle or cost_per_hours):
                line_ids = account_analytic_line.search([('name', 'ilike', workcenter_line.name)])
                self.assertTrue(line_ids, 'Costs lines are not generated.')
                for line in account_analytic_line.browse(line_ids):
                    if workcenter.costs_hour_account_id and line.account_id.id == workcenter.costs_hour_account_id.id:
                        self.assertEqual(rounding(line.unit_amount, 3), rounding(workcenter_line.hour, 3), "Cost Unit Amount is not correspond.")
                        self.assertEqual(rounding(line.amount, 3), rounding(cost_per_hours, 3), "Cost amount is not correspond.")
                    elif workcenter.costs_cycle_account_id and line.account_id.id == workcenter.costs_cycle_account_id.id:
                        self.assertEqual(rounding(line.unit_amount, 3), rounding(workcenter_line.cycle, 3), "Cost Unit Amount is not correspond.")
                        self.assertEqual(rounding(line.amount, 3), rounding(cost_per_cyle, 3), "Cost Amount is not correspond.")
                    else:
                        raise AssertionError('unknown cost line: %s' % line)
                    self.assertEqual(line.general_account_id.id, workcenter.costs_general_account_id.id, "General Account is not correspond.")
                    self.assertEqual(line.journal_id.id, workcenter.costs_journal_id.id, "Account Journal is not correspond.")
                    self.assertEqual(line.product_id.id, workcenter.product_id.id, "Product does not correspond.")
                    self.assertEqual(line.product_uom.id, workcenter.product_id.uom_id.id, "UOM does not correspond.")
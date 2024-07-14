# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mrp_account.tests.test_mrp_account import TestMrpAccount
from odoo.tests.common import Form
from odoo import Command
from freezegun import freeze_time


class TestReportsCommon(TestMrpAccount):

    def test_mrp_cost_structure(self):
        """ Check that values of mrp_cost_structure are correctly calculated even when:
        1. byproducts with a cost share.
        2. multi-company + multi-currency environment.
        """

        # create MO with component cost + operations cost
        self.product_table_sheet.standard_price = 20.0
        self.product_table_leg.standard_price = 5.0
        self.product_bolt.standard_price = 1.0
        self.product_screw.standard_price = 2.0
        self.product_table_leg.tracking = 'none'
        self.product_table_sheet.tracking = 'none'
        self.mrp_workcenter.costs_hour = 50.0

        bom = self.mrp_bom_desk.copy()
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = self.dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 1
        production_table = production_table_form.save()

        # add a byproduct w/ a non-zero cost share
        byproduct_cost_share = 10
        byproduct = self.env['product.product'].create({
            'name': 'Plank',
            'type': 'product',
        })

        self.env['stock.move'].create({
            'name': "Byproduct",
            'product_id': byproduct.id,
            'product_uom': byproduct.uom_id.id,
            'product_uom_qty': 1,
            'production_id': production_table.id,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'cost_share': byproduct_cost_share
        })

        production_table.action_confirm()
        mo_form = Form(production_table)
        mo_form.qty_producing = 1
        production_table = mo_form.save()

        # add operation duration otherwise 0 operation cost
        self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': self.mrp_workcenter.id,
            'date_start': datetime.now() - timedelta(minutes=30),
            'date_end': datetime.now(),
            'loss_id': self.env.ref('mrp.block_reason7').id,
            'description': self.env.ref('mrp.block_reason7').name,
            'workorder_id': production_table.workorder_ids[0].id
        })

        # avoid qty done not being updated when enterprise mrp_workorder is installed
        for move in production_table.move_raw_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        production_table._post_inventory()
        production_table.button_mark_done()

        total_component_cost = sum(move.product_id.standard_price * move.quantity for move in production_table.move_raw_ids)
        total_operation_cost = sum(wo.costs_hour * sum(wo.time_ids.mapped('duration')) / 60.0 for wo in production_table.workorder_ids)

        report = self.env['report.mrp_account_enterprise.mrp_cost_structure']
        self.env.flush_all()  # flush to avoid the wo duration not being available in the db in order to correctly build report
        report_values = report._get_report_values(docids=production_table.id)['lines'][0]
        self.assertEqual(report_values['component_cost_by_product'][self.dining_table], total_component_cost * (100 - byproduct_cost_share) / 100)
        self.assertEqual(report_values['operation_cost_by_product'][self.dining_table], total_operation_cost * (100 - byproduct_cost_share) / 100)
        self.assertEqual(report_values['component_cost_by_product'][byproduct], total_component_cost * byproduct_cost_share / 100)
        self.assertEqual(report_values['operation_cost_by_product'][byproduct], total_operation_cost * byproduct_cost_share / 100)

        # create another company w/ different currency + rate
        exchange_rate = 4
        currency_p = self.env['res.currency'].create({
            'name': 'DBL',
            'symbol': 'DD',
            'rounding': 0.01,
            'currency_unit_label': 'Doubloon'
        })
        company_p = self.env['res.company'].create({'name': 'Pirates R Us', 'currency_id': currency_p.id})
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': exchange_rate,
            'currency_id': self.env.company.currency_id.id,
            'company_id': company_p.id,
        })

        user_p = self.env['res.users'].create({
            'name': 'pirate',
            'login': 'pirate',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('mrp.group_mrp_manager').id])],
            'company_id': company_p.id,
            'company_ids': [(6, 0, [company_p.id, self.env.company.id])]
        })

        report_values = report.with_user(user_p)._get_report_values(docids=production_table.id)['lines'][0]
        self.assertEqual(report_values['component_cost_by_product'][self.dining_table], total_component_cost * (100 - byproduct_cost_share) / 100 / exchange_rate)
        self.assertEqual(report_values['operation_cost_by_product'][self.dining_table], total_operation_cost * (100 - byproduct_cost_share) / 100 / exchange_rate)
        self.assertEqual(report_values['component_cost_by_product'][byproduct], total_component_cost * byproduct_cost_share / 100 / exchange_rate)
        self.assertEqual(report_values['operation_cost_by_product'][byproduct], total_operation_cost * byproduct_cost_share / 100 / exchange_rate)

    @freeze_time('2022-05-28')
    def test_mrp_avg_cost_calculation(self):
        """
            Check that the average cost is calculated based on the quantity produced in each MO

            - Final product Bom structure:
                - product_4: qty: 2, cost: $20
                - product_3: qty: 3, cost: $50

            - Work center > costs_hour = $80

            1:/ MO1:
                - qty to produce: 10 units
                - work_order duration: 300
                unit_component_cost = ((20 * 2) + (50 * 3)) = 190
                unit_duration = 300 / 10 = 30
                unit_operation_cost = (80 / 60) * 30'unit_duration' = 40
                unit_cost = 190 + 40 = 250

            2:/ MO2:
                - update product_3 cost to: $30
                - qty to produce: 20 units
                - work order duration: 600
                unit_component_cost = ((20 * 2) + (30 * 3)) = $130
                unit_duration = 600 / 20 = 30
                unit_operation_cost = (80 / 60) * 30'unit_duration' = 40
                unit_cost = 130 + 40 = 170

            total_qty_produced = 30
            avg_unit_component_cost = ((190 * 10) + (130 * 20)) / 30 = $150
            avg_unit_operation_cost = ((40*20) + (40*10)) / 30 = $40
            avg_unit_duration = (600 + 300) / 30 = 30
            avg_unit_cost = avg_unit_component_cost + avg_unit_operation_cost = $190
        """

        # Make some stock and reserve
        for product in self.bom_2.bom_line_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1000,
                'location_id': self.stock_location_components.id,
            })._apply_inventory()

        # Change product_4 UOM to unit
        self.bom_2.bom_line_ids[0].product_uom_id = self.ref('uom.product_uom_unit')

        # Update the work center cost
        self.bom_2.operation_ids.workcenter_id.costs_hour = 80

        # MO_1
        self.product_4.standard_price = 20
        self.product_3.standard_price = 50
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_2
        production_form.product_qty = 10
        mo_1 = production_form.save()
        mo_1.action_confirm()

        mo_1.button_plan()
        wo = mo_1.workorder_ids
        wo.button_start()
        wo.duration = 300
        wo.qty_producing = 10

        mo_1.button_mark_done()

        # MO_2
        self.product_3.standard_price = 30
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_2
        production_form.product_qty = 20
        mo_2 = production_form.save()
        mo_2.action_confirm()

        mo_2.button_plan()
        wo = mo_2.workorder_ids
        wo.button_start()
        wo.duration = 600
        wo.qty_producing = 20

        mo_2.button_mark_done()

        # must flush else SQL request in report is not accurate
        self.env.flush_all()

        report = self.env['mrp.report']._read_group(
            [('product_id', '=', self.bom_2.product_id.id)],
            aggregates=['unit_cost:avg', 'unit_component_cost:avg', 'unit_operation_cost:avg', 'unit_duration:avg'],
        )[0]
        unit_cost, unit_component_cost, unit_operation_cost, unit_duration = report
        self.assertEqual(unit_cost, 190)
        self.assertEqual(unit_component_cost, 150)
        self.assertEqual(unit_operation_cost, 40)
        self.assertEqual(unit_duration, 30)

    def test_multiple_users_operation(self):
        """ Check what happens on the report when two users log on the same operation simultaneously.
        """
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        user_1 = self.env['res.users'].create({
            'name': 'Lonie',
            'login': 'lonie',
            'email': 'lonie@user.com',
            'groups_id': [Command.set([self.env.ref('mrp.group_mrp_user').id])],
        })
        user_2 = self.env['res.users'].create({
            'name': 'Doppleganger',
            'login': 'dopple',
            'email': 'dopple@user.com',
            'groups_id': [Command.set([self.env.ref('mrp.group_mrp_user').id])],
        })

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_4
        production = production_form.save()
        with Form(production) as mo_form:
            with mo_form.workorder_ids.new() as wo:
                wo.name = 'Do important stuff'
                wo.workcenter_id = self.workcenter_2
        production.action_confirm()

        # Have both users working simultaneously on the same operation
        self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': self.workcenter_2.id,
            'date_start': datetime.now() - timedelta(minutes=30),
            'date_end': datetime.now(),
            'loss_id': self.env.ref('mrp.block_reason7').id,
            'workorder_id': production.workorder_ids[0].id,
            'user_id': user_1.id,
        })
        self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': self.workcenter_2.id,
            'date_start': datetime.now() - timedelta(minutes=20),
            'date_end': datetime.now() - timedelta(minutes=5),
            'loss_id': self.env.ref('mrp.block_reason7').id,
            'workorder_id': production.workorder_ids[0].id,
            'user_id': user_2.id,
        })
        production.button_mark_done()
        # Need to flush to have the duration correctly set on the workorders for the report.
        self.env.flush_all()

        cost_analysis = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(production)[0]
        workcenter_times = list(filter(lambda op: op[0] == self.workcenter_2.name and op[2] == production.workorder_ids[0].name, cost_analysis['operations']))

        self.assertEqual(len(workcenter_times), 1, "There should be only a single line for the workcenter cost")
        self.assertEqual(workcenter_times[0][3], production.workorder_ids[0].duration / 60, "Duration should be the total duration of this operation.")

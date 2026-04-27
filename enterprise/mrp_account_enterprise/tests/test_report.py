# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mrp_account.tests.test_mrp_account import TestMrpAccount
from odoo.tests import Form
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
            'is_storable': True,
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
        bom = self.bom_2.copy()
        bom.type = 'normal'
        bom.product_id = self.product_6

        # Make some stock and reserve
        for product in bom.bom_line_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1000,
                'location_id': self.stock_location_components.id,
            })._apply_inventory()

        # Change product_4 UOM to unit
        bom.bom_line_ids[0].product_uom_id = self.ref('uom.product_uom_unit')

        # Update the work center cost
        bom.operation_ids.workcenter_id.costs_hour = 80

        # MO_1
        self.product_4.standard_price = 20
        self.product_3.standard_price = 50
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = bom
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
        production_form.bom_id = bom
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
            [('product_id', '=', bom.product_id.id)],
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

    @freeze_time('2022-05-28')
    def test_cost_analysis_mismatch_in_produced_and_planned_quantity(self):
        '''
        verify that the Cost Analysis report correctly reflects the actual
        quantity produced and cost per unit when it differs from the planned quantity.

        '''
        # enable by-product
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_byproducts')
        self.product_3.standard_price = 10
        self.product_4.standard_price = 10
        bom_1 = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_3.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.product_4.id, 'product_qty': 1})
            ],
            'byproduct_ids': [
                Command.create({
                    'product_id': self.product_2.id,
                    'product_uom_id': self.product_2.uom_id.id,
                    'product_qty': 1,
                }),
            ],
        })
        # Make some stock and reserve
        for product in bom_1.bom_line_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1000,
                'location_id': self.stock_location_components.id,
            })._apply_inventory()

        # first MO set qty as 1 produce 5
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = bom_1
        production_form.product_qty = 1
        mo = production_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        # 4 dozen of byproduct
        with mo_form.move_byproduct_ids.edit(0) as line:
            line.product_uom = self.env.ref('uom.product_uom_dozen')
            line.quantity = 4
            line.cost_share = 48
        mo_done = mo_form.save()
        mo_done.button_mark_done()

        self.env.flush_all()

        cost_analysis = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(mo_done)

        self.assertEqual(cost_analysis[0]['mo_qty'], 5)
        self.assertEqual(cost_analysis[0]['total_cost'], 100)
        # 4 * dozen = 48 units of by product
        self.assertEqual(cost_analysis[0]['qty_by_byproduct'][self.product_2], 48)
        self.assertEqual(cost_analysis[0]['total_cost_by_product'][self.product_2], 48)

        # first MO set qty as 5 produce 1 without a backorder
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = bom_1
        production_form.product_qty = 5
        no_backorder_mo = production_form.save()
        no_backorder_mo.action_confirm()
        no_backorder_mo_form = Form(no_backorder_mo)
        no_backorder_mo_form.qty_producing = 1
        no_backorder_mo_done = no_backorder_mo_form.save()
        action = no_backorder_mo_done.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_close_mo()

        self.env.flush_all()

        cost_analysis = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(no_backorder_mo_done)
        self.assertEqual(cost_analysis[0]['mo_qty'], 1)
        self.assertEqual(cost_analysis[0]['total_cost'], 20)
        # Test that cost analysis is correct when multiple MOs are grouped
        cost_analysis = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(no_backorder_mo_done | mo_done)
        self.assertEqual(cost_analysis[0]['mo_qty'], 6)
        self.assertEqual(cost_analysis[0]['total_cost'], 120)
        self.assertEqual(cost_analysis[0]['total_cost_components'], 120)

    def test_scrap_is_in_report(self):
        """
            This test ensures that the report correctly reflects the quantities and uoms
            for the scraps of manufactured products and their components.
            The manufactured product's uom is set to dozen, while the scraps are in units.
        """
        self.product_2.standard_price = 10
        self.planning_bom.product_qty = 1

        # Create a manufacturing order (MO) with product UoM as dozen
        mo = self.env['mrp.production'].create({
            'bom_id': self.planning_bom.id,
            'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_2, mo.location_dest_id, 100)
        mo.action_confirm()

        # scrap one unit of component
        scrap_component = self.env['stock.scrap'].create({
            'product_id': self.product_2.id,
            'scrap_qty': 2,
            'production_id': mo.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        scrap_component.action_validate()
        mo.button_mark_done()

        # scrap one unit of manufactured product
        scrap_finished_product = self.env['stock.scrap'].create({
            'product_id': self.planning_bom.product_id.id,
            'scrap_qty': 1,
            'production_id': mo.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        scrap_finished_product.action_validate()
        self.env.flush_all()

        cost_analysis = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(mo)
        # Assert the MO quantity is in the product uom (12 units per dozen)
        self.assertEqual(cost_analysis[0]['mo_qty'], 12)
        # Assert the total cost (12 units * 10 per unit * 2 components)
        self.assertEqual(cost_analysis[0]['total_cost'], 240)

        # Assert that the scraps are present and quantities match expectations
        scrap_lines = cost_analysis[0]['scraps']
        self.assertEqual(len(scrap_lines), 2)

        # Check component scrap
        component_scrap_line = scrap_lines[0]
        self.assertEqual(component_scrap_line['product_id'], self.product_2)
        self.assertEqual(component_scrap_line['quantity'], 2)
        self.assertEqual(component_scrap_line['product_uom'], self.env.ref('uom.product_uom_unit'))

        # Check finished product scrap
        finished_product_scrap_line = scrap_lines[1]
        self.assertEqual(finished_product_scrap_line['product_id'], self.planning_bom.product_id)
        self.assertEqual(finished_product_scrap_line['quantity'], 1)
        self.assertEqual(finished_product_scrap_line['product_uom'], self.env.ref('uom.product_uom_unit'))

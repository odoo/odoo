# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.stock_account.tests.test_account_move import TestAccountMoveStockCommon
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user


class TestMrpAccount(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpAccount, cls).setUpClass()
        cls.source_location_id = cls.stock_location_14.id
        cls.warehouse = cls.env.ref('stock.warehouse0')
        # setting up alternative workcenters
        cls.wc_alt_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter bis',
            'default_capacity': 3,
            'time_start': 9,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.wc_alt_2 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter ter',
            'default_capacity': 1,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 85,
        })
        cls.product_4.uom_id = cls.uom_unit
        cls.planning_bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_4.id,
            'product_tmpl_id': cls.product_4.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 4.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 4})
            ]})
        cls.dining_table = cls.env['product.product'].create({
            'name': 'Table (MTO)',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.product_table_sheet = cls.env['product.product'].create({
            'name': 'Table Top',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.product_table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'type': 'product',
            'tracking': 'lot',
        })
        cls.product_bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'type': 'product',
        })
        cls.product_screw = cls.env['product.product'].create({
            'name': 'Screw',
            'type': 'product',
        })

        cls.mrp_workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_bom_desk = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.dining_table.product_tmpl_id.id,
            'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
            'sequence': 3,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'workcenter_id': cls.mrp_workcenter.id, 'name': 'Manual Assembly'}),
            ],
        })
        cls.mrp_bom_desk.write({
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.product_table_sheet.id,
                    'product_qty': 1,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 1,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_table_leg.id,
                    'product_qty': 4,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 2,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_bolt.id,
                    'product_qty': 4,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 3,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_screw.id,
                    'product_qty': 10,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 4,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
            ]
        })
        cls.mrp_workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Drill Station 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.categ_standard = cls.env['product.category'].create({
            'name': 'STANDARD',
            'property_cost_method': 'standard'
        })
        cls.categ_real = cls.env['product.category'].create({
            'name': 'REAL',
            'property_cost_method': 'fifo'
        })
        cls.categ_average = cls.env['product.category'].create({
            'name': 'AVERAGE',
            'property_cost_method': 'average'
        })
        cls.dining_table.categ_id = cls.categ_real.id
        cls.product_table_sheet.categ_id = cls.categ_real.id
        cls.product_table_leg.categ_id = cls.categ_average.id
        cls.product_bolt.categ_id = cls.categ_standard.id
        cls.product_screw.categ_id = cls.categ_standard.id
        cls.env['stock.move'].search([('product_id', 'in', [cls.product_bolt.id, cls.product_screw.id])])._do_unreserve()
        (cls.product_bolt + cls.product_screw).write({'type': 'product'})
        cls.dining_table.tracking = 'none'

    def test_00_production_order_with_accounting(self):
        self.product_table_sheet.standard_price = 20.0
        self.product_table_leg.standard_price = 15.0
        self.product_bolt.standard_price = 10.0
        self.product_screw.standard_price = 0.1
        self.product_table_leg.tracking = 'none'
        self.product_table_sheet.tracking = 'none'
        # Inventory Product Table
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_table_sheet.id,  # tracking serial
            'inventory_quantity': 20,
            'location_id': self.source_location_id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_table_leg.id,  # tracking lot
            'inventory_quantity': 20,
            'location_id': self.source_location_id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_bolt.id,
            'inventory_quantity': 20,
            'location_id': self.source_location_id,
        })
        quants |= self.env['stock.quant'].create({
            'product_id': self.product_screw.id,
            'inventory_quantity': 200000,
            'location_id': self.source_location_id,
        })
        quants.action_apply_inventory()

        bom = self.mrp_bom_desk.copy()
        bom.bom_line_ids.manual_consumption = False
        bom.operation_ids = False
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = self.dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 1
        production_table = production_table_form.save()

        production_table.extra_cost = 20
        production_table.action_confirm()

        mo_form = Form(production_table)
        mo_form.qty_producing = 1
        production_table = mo_form.save()
        production_table._post_inventory()
        move_value = production_table.move_finished_ids.filtered(lambda x: x.state == "done").stock_valuation_layer_ids.value

        # 1 table head at 20 + 4 table leg at 15 + 4 bolt at 10 + 10 screw at 10 + 1*20 (extra cost)
        self.assertEqual(move_value, 141, 'Thing should have the correct price')

    def test_stock_user_without_account_permissions_can_create_bom(self):
        mrp_manager = new_test_user(
            self.env, 'temp_mrp_manager', 'mrp.group_mrp_manager,product.group_product_variant',
        )

        bom_form = Form(self.env['mrp.bom'].with_user(mrp_manager))
        bom_form.product_id = self.dining_table

    def test_two_productions_unbuild_one_sell_other_fifo(self):
        """ Unbuild orders, when supplied with a specific MO record, should restrict their SVL
        consumption to layers linked to moves originating from that MO record.
        """
        final_product = self.env['product.product'].create({
            'type': 'product',
            'name': 'final product',
            'categ_id': self.categ_real.id,
        })
        component = self.env['product.product'].create({
            'type': 'product',
            'name': 'component',
            'standard_price': 1.0,
            'categ_id': self.categ_standard.id,
        })
        final_bom = self.env['mrp.bom'].create({
            'product_id': final_product.id,
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({
                'product_id': component.id,
                'product_qty': 1,
            })],
        })
        in_move = self.env['stock.move'].create({
            'name': 'in 2 component',
            'product_id': component.id,
            'product_uom_qty': 2.0,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.source_location_id,
            'price_unit': 1,
        })
        in_move._action_confirm()
        in_move._action_assign()
        in_move.picked = True
        in_move._action_done()
        mo_1 = self.env['mrp.production'].create({'product_id': final_product.id})
        mo_1.action_confirm()
        mo_1.action_assign()
        mo_1.button_mark_done()
        self.assertRecordValues(
            self.env['stock.valuation.layer'].search([('product_id', '=', (final_product.id))]),
            # MO_1
            [{'remaining_qty': 1.0, 'value': 1.0}]
        )

        with Form(component) as comp_form:
            comp_form.standard_price = 2
        mo_2 = self.env['mrp.production'].create({'product_id': final_product.id})
        mo_2.action_confirm()
        mo_2.action_assign()
        mo_2.button_mark_done()
        self.assertRecordValues(
            self.env['stock.valuation.layer'].search([('product_id', '=', (final_product.id))]),
            [
                {'remaining_qty': 1.0, 'value': 1.0},
                # MO_2 (new value to reflect change of component's `standard_price`
                {'remaining_qty': 1.0, 'value': 2.0},
            ]
        )
        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.product_id = final_product
        unbuild_form.bom_id = final_bom
        unbuild_form.product_qty = 1
        unbuild_form.mo_id = mo_2
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()
        self.assertRecordValues(
            self.env['stock.valuation.layer'].search([('product_id', '=', (final_product.id))]),
            [
                {'remaining_qty': 1.0, 'value': 1.0},
                {'remaining_qty': 0.0, 'value': 2.0},
                # Unbuild SVL value is derived from MO_2, as precised on the unbuild form
                {'remaining_qty': 0.0, 'value': -2.0, 'quantity': 1.0},
            ]
        )
        out_move = self.env['stock.move'].create({
            'name': 'out 1 final',
            'product_id': final_product.id,
            'product_uom_qty': 1.0,
            'location_id': self.source_location_id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        out_move._action_confirm()
        out_move._action_assign()
        out_move.quantity = 1
        out_move.picked = True
        out_move._action_done()
        self.assertRecordValues(
            self.env['stock.valuation.layer'].search([('product_id', '=', (final_product.id))]),
            [
                {'remaining_qty': 0.0, 'value': 1.0},
                {'remaining_qty': 0.0, 'value': 2.0},
                {'remaining_qty': 0.0, 'value': -2.0},
                # Out move SVL value is derived from MO_1, the only candidate origin with some `remaining_qty`
                {'remaining_qty': 0.0, 'value': -1.0, 'quantity': 1.0},
            ]
        )

@tagged("post_install", "-at_install")
class TestMrpAccountMove(TestAccountMoveStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.production_account = cls.env['account.account'].create({
            'name': 'Cost of Production',
            'code': 'ProductionCost',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        cls.auto_categ.property_stock_account_production_cost_id = cls.production_account
        cls.product_B = cls.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "default_code": "prda",
                "categ_id": cls.auto_categ.id,
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(5, 0, 0)],
                "lst_price": 100.0,
                "standard_price": 10.0,
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
                "property_account_expense_id": cls.company_data["default_account_expense"].id,
            }
        )
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_A.id,
            'product_tmpl_id': cls.product_A.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_B.id, 'product_qty': 1}),
            ]})

    def test_unbuild_account_00(self):
        """Test when after unbuild, the journal entries are the reversal of the
        journal entries created when produce the product.
        """
        # build
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_A
        production_form.bom_id = self.bom
        production_form.product_qty = 1
        production = production_form.save()
        production.action_confirm()
        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()
        production._post_inventory()
        production.button_mark_done()

        # finished product move
        productA_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product A'), ('credit', '=', 0)])
        productA_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product A'), ('debit', '=', 0)])
        self.assertEqual(productA_debit_line.account_id, self.stock_valuation_account)
        self.assertEqual(productA_credit_line.account_id, self.production_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.production_account)
        self.assertEqual(productB_credit_line.account_id, self.stock_valuation_account)

        # unbuild
        res_dict = production.button_unbuild()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.action_validate()

        # finished product move
        productA_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('credit', '=', 0)])
        productA_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('debit', '=', 0)])
        self.assertEqual(productA_debit_line.account_id, self.production_account)
        self.assertEqual(productA_credit_line.account_id, self.stock_valuation_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.stock_valuation_account)
        self.assertEqual(productB_credit_line.account_id, self.production_account)

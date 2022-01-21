# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.stock_account.tests.test_account_move import TestAccountMove
from odoo.tests import Form, tagged


class TestMrpAccount(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpAccount, cls).setUpClass()
        cls.source_location_id = cls.stock_location_14.id
        cls.warehouse = cls.env.ref('stock.warehouse0')
        # setting up alternative workcenters
        cls.wc_alt_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter bis',
            'capacity': 3,
            'time_start': 9,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.wc_alt_2 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter ter',
            'capacity': 1,
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
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.product_table_sheet.id,  # tracking serial
                'product_uom_id': self.product_table_sheet.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_table_leg.id,  # tracking lot
                'product_uom_id': self.product_table_leg.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_bolt.id,
                'product_uom_id': self.product_bolt.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_screw.id,
                'product_uom_id': self.product_screw.uom_id.id,
                'product_qty': 200000,
                'location_id': self.source_location_id
            }),
            ]
        })
        inventory.action_validate
        bom = self.mrp_bom_desk.copy()
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


@tagged("post_install", "-at_install")
class TestMrpAccountMove(TestAccountMove):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_B = cls.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "default_code": "prda",
                "categ_id": cls.env.ref("product.product_category_all").id,
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
        self.assertEqual(productA_credit_line.account_id, self.stock_input_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.stock_output_account)
        self.assertEqual(productB_credit_line.account_id, self.stock_valuation_account)

        # unbuild
        res_dict = production.button_unbuild()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.action_validate()

        # finished product move
        productA_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('credit', '=', 0)])
        productA_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('debit', '=', 0)])
        self.assertEqual(productA_debit_line.account_id, self.stock_input_account)
        self.assertEqual(productA_credit_line.account_id, self.stock_valuation_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.stock_valuation_account)
        self.assertEqual(productB_credit_line.account_id, self.stock_output_account)

    def test_unbuild_account_01(self):
        """Test when production location has its valuation accounts. After unbuild,
        the journal entries are the reversal of the journal entries created when
        produce the product.
        """
        # set accounts for production location
        production_location = self.product_A.property_stock_production
        wip_incoming_account = self.env['account.account'].create({
            'name': 'wip incoming',
            'code': '000001',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        wip_outgoing_account = self.env['account.account'].create({
            'name': 'wip outgoing',
            'code': '000002',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        production_location.write({
            'valuation_in_account_id': wip_incoming_account.id,
            'valuation_out_account_id': wip_outgoing_account.id,
        })

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
        self.assertEqual(productA_credit_line.account_id, wip_outgoing_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'MO%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, wip_incoming_account)
        self.assertEqual(productB_credit_line.account_id, self.stock_valuation_account)

        # unbuild
        res_dict = production.button_unbuild()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.action_validate()

        productA_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('credit', '=', 0)])
        productA_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product A'), ('debit', '=', 0)])
        self.assertEqual(productA_debit_line.account_id, wip_outgoing_account)
        self.assertEqual(productA_credit_line.account_id, self.stock_valuation_account)
        # component move
        productB_debit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('ref', 'ilike', 'UB%Product B'), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.stock_valuation_account)
        self.assertEqual(productB_credit_line.account_id, wip_incoming_account)

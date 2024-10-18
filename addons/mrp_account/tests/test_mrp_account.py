# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.stock_account.tests.test_account_move import TestAccountMoveStockCommon
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user
from odoo import fields, Command


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
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.product_table_sheet = cls.env['product.product'].create({
            'name': 'Table Top',
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.product_table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.product_bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'is_storable': True,
        })
        cls.product_screw = cls.env['product.product'].create({
            'name': 'Screw',
            'is_storable': True,
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
        (cls.product_bolt + cls.product_screw).write({'is_storable': True})
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
                "is_storable": True,
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
        cls.product_C = cls.env["product.product"].create(
            {
                "name": "Product C",
                "is_storable": True,
                "default_code": "prdc",
                "categ_id": cls.auto_categ.id,
            }
        )
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_A.id,
            'product_tmpl_id': cls.product_A.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_B.id, 'product_qty': 1}),
            ]})
        # if for some reason this default property doesn't exist, the tests that reference it will fail due to missing journal
        field = cls.env['product.category']._fields['property_stock_valuation_account_id']
        cls.default_sv_account_id = field.get_company_dependent_fallback(cls.env['product.category']).id
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'default_capacity': 1,
            'time_efficiency': 100,
        })

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
        Form.from_action(self.env, production.button_unbuild()).save().action_validate()

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

    def test_wip_accounting_00(self):
        """ Test that posting a WIP accounting entry works as expected.
        WIP MO = MO with some time completed on WOs and/or 'consumed' components
        """
        self.env.user.write({'groups_id': [(4, self.env.ref('mrp.group_mrp_routings').id)]})
        wc = self.env['mrp.workcenter'].create({
            'name': 'Funland',
            'time_start': 0,
            'time_stop': 0,
            'costs_hour': 100,
        })

        self.bom.write({
            'operation_ids': [
                (0, 0, {
                    'name': 'Fun Operation',
                    'workcenter_id': wc.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 20,
                    'sequence': 1,
                }),
            ],
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_A
        mo_form.bom_id = self.bom
        mo_form.product_qty = 1
        mo = mo_form.save()

        # post a WIP for an invalid MO, i.e. draft/cancelled/done results in a "Manual Entry"
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.save().confirm()
        wip_manual_entry1 = self.env['account.move'].search([('ref', 'ilike', 'WIP - Manual Entry')])
        self.assertEqual(len(wip_manual_entry1), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_manual_entry1[0].wip_production_count, 0, "Non-WIP MOs shouldn't be linked to manual entry")
        self.assertEqual(len(wip_manual_entry1.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_manual_entry1.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
        ])

        # post a WIP for a valid MO - no WO time completed or components consumed => nothing to debit/credit
        mo.action_confirm()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.save().confirm()
        wip_empty_entries = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name)])
        self.assertEqual(len(wip_empty_entries), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_empty_entries[0].wip_production_count, 1, "WIP MOs should be linked to entries even if no 'done' work")
        self.assertEqual(len(wip_empty_entries.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_empty_entries.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
        ])

        # WO time completed + components consumed
        mo_form = Form(mo)
        mo_form.qty_producing = mo.product_qty
        mo = mo_form.save()
        now = fields.Datetime.now()
        workorder = mo.workorder_ids
        self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': wc.id,
            'workorder_id': workorder.id,
            'date_start': now - timedelta(hours=1),
            'date_end': now,
            'loss_id': self.env.ref('mrp.block_reason7').id,
        })
        workorder.button_done()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.save().confirm()
        wip_entries1 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', wip_empty_entries.ids)])
        self.assertEqual(len(wip_entries1), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_entries1[0].wip_production_count, 1, "WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries1.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_entries1.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': self.product_B.standard_price,          'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0,                                  'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0,                                    'credit': 100.0 + self.product_B.standard_price},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0,                                    'credit': self.product_B.standard_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0,                                    'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 100.0 + self.product_B.standard_price,  'credit': 0.0},
        ])

        # Multi-records case
        previous_wip_ids = wip_entries1.ids + wip_empty_entries.ids
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = self.product_A
        mo2_form.bom_id = self.bom
        mo2_form.product_qty = 2
        mo2 = mo2_form.save()
        mos = (mo | mo2)

        # Draft MOs should be ignored when selecting multiple MOs
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries2 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries2), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for 1 MO")
        self.assertTrue(mo2.name not in wip_entries2[0].ref, "Draft MO should be completely disregarded by wizard")
        self.assertEqual(wip_entries2[0].wip_production_count, 1, "Only WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries2.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = self.product_B.standard_price * sum(mo.move_raw_ids.mapped('quantity'))
        self.assertRecordValues(wip_entries2.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': total_component_price,         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0,                         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0,                           'credit': 100.0 + total_component_price},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0,                           'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0,                           'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])
        previous_wip_ids += wip_entries2.ids

        # MOs' WIP amounts should be aggregated
        mo2.action_confirm()
        mo2_form = Form(mo2)
        mo2_form.qty_producing = mo2.product_qty
        mo2 = mo2_form.save()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries3 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries3), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for both MOs")
        self.assertTrue(mo2.name in wip_entries3[0].ref, "Both MOs should have been considered")
        self.assertEqual(wip_entries3[0].wip_production_count, 2, "Both WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries3.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = self.product_B.standard_price * sum(mos.move_raw_ids.mapped('quantity'))
        self.assertRecordValues(wip_entries3.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': total_component_price,         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0,                         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0,                           'credit': 100.0 + total_component_price},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0,                           'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0,                           'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])
        previous_wip_ids += wip_entries3.ids

        # Done MO should be ignored
        mo2.button_mark_done()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries4 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries4), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for 1 MO")
        self.assertTrue(mo2.name not in wip_entries4[0].ref, "Done MO should be completely disregarded by wizard")
        self.assertEqual(wip_entries4[0].wip_production_count, 1, "Only WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries4.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = self.product_B.standard_price * sum(mo.move_raw_ids.mapped('quantity'))
        self.assertRecordValues(wip_entries4.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': total_component_price,         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0,                         'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0,                           'credit': 100.0 + total_component_price},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0,                           'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0,                           'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])
        previous_wip_ids += wip_entries4.ids

        # WO time completed + components consumed, but WIP date is for before they were done => nothing to debit/credit
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.date = now - timedelta(days=2)
        wizard.save().confirm()
        wip_entries5 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries5), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_entries5[0].wip_production_count, 1, "WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries5.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_entries5.line_ids, [
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
            {'account_id': self.default_sv_account_id,                                     'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id,          'debit': 0.0, 'credit': 0.0},
        ])

    def test_labor_cost_balancing(self):
        """ When the workcenter_cost ends up like x.xx5 with a currency rounding of 0.01,
        the valuation 'account.move' was unbalanced.
        This happened because the credit value rounded up twice, and instead of having -0.005 + 0.005 => 0,
        we had -0 + 0.01 => +0.01, which made the credit differ from the debit by 0.01.
        This test ensures that if the workcenter_cost is rounded to 0.01, then the credit value is correctly
        decremented by 0.01.
        """
        # Setup
        self.workcenter.write({'costs_hour': 10})
        self.bom.write({
            'operation_ids': [
                Command.create({'name': 'work', 'workcenter_id': self.workcenter.id, 'time_cycle': 5, 'sequence': 1}),
            ],
        })

        # Build
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_A
        production_form.bom_id = self.bom
        production_form.product_qty = 1
        production = production_form.save()
        production.action_confirm()
        workorder = production.workorder_ids
        workorder.duration = 0.03  # ~= 2 seconds (1.8 seconds exactly)
        workorder.time_ids.write({'duration': 0.03})  # Ensure that the duration is correct
        self.assertEqual(workorder._cal_cost(), 0.005)  # 2 seconds at $10/h

        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()
        production._post_inventory()
        production.button_mark_done()

        account_move = production.move_finished_ids.stock_valuation_layer_ids.account_move_id
        self.assertRecordValues(account_move.line_ids, [
            {'credit': 10.0, 'debit': 0.00},  # Credit Line
            {'credit': 0.00, 'debit': 10.00},  # Debit Line
        ])
        labour_move = workorder.time_ids.account_move_line_id.move_id
        self.assertRecordValues(labour_move.line_ids, [
            {'credit': 0.01, 'debit': 0.00},
            {'credit': 0.00, 'debit': 0.01},
        ])

    def test_labor_cost_balancing_with_cost_share(self):
        """ Same test as test_labor_cost_balancing, however, instead of having the worcenter_cost to 0.05,
        we have it at 0.01, and it is the cost_share that bring it back to 0.005 before rounding it back up to 0.01.
        """
        # Setup
        self.workcenter.write({'costs_hour': 20})
        self.bom.write({
            'operation_ids': [
                Command.create({'name': 'work', 'workcenter_id': self.workcenter.id, 'time_cycle': 5, 'sequence': 1}),
            ],
            'byproduct_ids': [Command.create({'product_id': self.product_C.id, 'product_qty': 1, 'cost_share': 50})],
        })

        # Build
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_A
        production_form.bom_id = self.bom
        production_form.product_qty = 1
        production = production_form.save()
        production.action_confirm()
        workorder = production.workorder_ids
        workorder.duration = 0.03  # ~= 2 seconds (1.8 seconds exactly)
        workorder.time_ids.write({'duration': 0.03})  # Ensure that the duration is correct
        self.assertEqual(workorder._cal_cost(), 0.01)  # 2 seconds at $20/h

        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()
        production._post_inventory()
        production.button_mark_done()

        account_move = production.move_finished_ids.filtered(lambda fm: fm.product_id == self.product_A) \
            .stock_valuation_layer_ids.account_move_id
        self.assertRecordValues(account_move.line_ids, [
            {'credit': 10.0, 'debit': 0.00},  # Credit Line
            {'credit': 0.00, 'debit': 10.00},  # Debit Line
        ])
        labour_move = workorder.time_ids.account_move_line_id.move_id
        self.assertRecordValues(labour_move.line_ids, [
            {'credit': 0.01, 'debit': 0.00},
            {'credit': 0.00, 'debit': 0.01},
        ])

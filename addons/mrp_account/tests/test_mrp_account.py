# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.mrp_account.tests.common import TestBomPriceCommon, TestBomPriceOperationCommon
from odoo.tests import Form
from odoo.tests.common import new_test_user
from odoo.tools import float_compare, float_round
from odoo import fields


class TestMrpAccount(TestBomPriceCommon):

    def test_00_production_order_with_accounting(self):
        # Inventory Product Table
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': self.leg.id,
            'inventory_quantity': 20,
            'location_id': self.stock_location.id,
        }, {
            'product_id': self.glass.id,
            'inventory_quantity': 20,
            'location_id': self.stock_location.id,
        }, {
            'product_id': self.screw.id,
            'inventory_quantity': 200000,
            'location_id': self.stock_location.id,
        }])
        quants.action_apply_inventory()

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = self.dining_table
        production_table_form.bom_id = self.bom_1
        production_table_form.product_qty = 1
        production_table = production_table_form.save()

        production_table.extra_cost = 20
        production_table.action_confirm()

        mo_form = Form(production_table)
        mo_form.qty_producing = 1
        production_table = mo_form.save()
        production_table.button_mark_done()
        move_value = production_table.move_finished_ids.filtered(lambda x: x.state == "done").value

        # 1 table head at 468.75 + 4 table leg at 25 + 1 glass at 100 + 5 screw at 10 + 1*20 (extra cost)
        self.assertEqual(move_value, 738.75, 'Thing should have the correct price')

    def test_stock_user_without_account_permissions_can_create_bom(self):
        mrp_manager = new_test_user(
            self.env, 'temp_mrp_manager', 'mrp.group_mrp_manager,product.group_product_variant',
        )

        bom_form = Form(self.env['mrp.bom'].with_user(mrp_manager))
        bom_form.product_id = self.dining_table

    def test_two_productions_unbuild_one_sell_other_fifo(self):
        """ Unbuild orders, when supplied with a specific MO record, should restrict their value
        consumption to moves originating from that MO record.
        """
        mo_1 = self._create_mo(self.bom_1, 1)
        mo_1.action_confirm()
        mo_1.action_assign()
        mo_1.button_mark_done()
        self.assertRecordValues(
            self.env['stock.move'].search([('product_id', '=', self.dining_table.id)]),
            # MO_1
            [{'remaining_qty': 1.0, 'value': 718.75}],
        )

        self.plywood_sheet.standard_price = 400
        mo_2 = self._create_mo(self.bom_1, 1)
        mo_2.action_confirm()
        mo_2.action_assign()
        mo_2.button_mark_done()
        self.assertRecordValues(
            self.env['stock.move'].search([('product_id', '=', self.dining_table.id)]),
            [
                {'remaining_qty': 1.0, 'value': 718.75},
                # MO_2 new value to reflect change of component's `standard_price`
                {'remaining_qty': 1.0, 'value': 918.75},
            ],
        )
        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.product_id = self.dining_table
        unbuild_form.bom_id = self.bom_1
        unbuild_form.product_qty = 1
        unbuild_form.mo_id = mo_2
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()
        self.assertRecordValues(
            self.env['stock.move'].search([('product_id', '=', self.dining_table.id)]),
            [
                {'remaining_qty': 0.0, 'value': 718.75, 'quantity': 1.0},
                {'remaining_qty': 1.0, 'value': 918.75, 'quantity': 1.0},
                # Unbuild move value is derived from MO_2, as precised on the unbuild form
                {'remaining_qty': 0.0, 'value': 718.75, 'quantity': 1.0},
            ],
        )
        self._make_out_move(self.dining_table, 1)
        self.assertRecordValues(
            self.env['stock.move'].search([('product_id', '=', self.dining_table.id)]),
            [
                {'remaining_qty': 0.0, 'value': 718.75, 'quantity': 1.0},
                {'remaining_qty': 0.0, 'value': 918.75, 'quantity': 1.0},
                {'remaining_qty': 0.0, 'value': 718.75, 'quantity': 1.0},
                # Out move value is derived from MO_1, the only candidate origin with some `remaining_qty`
                {'remaining_qty': 0.0, 'value': 918.75, 'quantity': 1.0},
            ],
        )

    def test_unbuild_account_00(self):
        """Test when after unbuild, the journal entries are the reversal of the
        journal entries created when produce the product.
        """
        # build
        production = self._create_mo(self.bom_1, 1)
        production.button_mark_done()

        # finished product move
        productA_debit_line = self.env['account.move.line'].search([('product_id', '=', self.dining_table.id), ('credit', '=', 0)])
        productA_credit_line = self.env['account.move.line'].search([('product_id', '=', self.dining_table.id), ('debit', '=', 0)])
        self.assertEqual(productA_debit_line.account_id, self.account_stock_valuation)
        self.assertEqual(productA_credit_line.account_id, self.account_production)
        # one of component move
        productB_debit_line = self.env['account.move.line'].search([('product_id', '=', self.glass.id), ('credit', '=', 0)])
        productB_credit_line = self.env['account.move.line'].search([('product_id', '=', self.glass.id), ('debit', '=', 0)])
        self.assertEqual(productB_debit_line.account_id, self.account_production)
        self.assertEqual(productB_credit_line.account_id, self.account_stock_valuation)

        # unbuild
        Form.from_action(self.env, production.button_unbuild()).save().action_validate()

        # finished product move
        productA_debit_line = self.env['account.move.line'].search([
            ('product_id', '=', self.dining_table.id),
            ('credit', '=', 0),
            ('name', 'ilike', 'UB'),
        ])
        productA_credit_line = self.env['account.move.line'].search([
            ('product_id', '=', self.dining_table.id),
            ('debit', '=', 0),
            ('name', 'ilike', 'UB'),
        ])
        self.assertEqual(productA_debit_line.account_id, self.account_production)
        self.assertEqual(productA_credit_line.account_id, self.account_stock_valuation)
        # component move
        productB_debit_line = self.env['account.move.line'].search([
            ('product_id', '=', self.glass.id),
            ('credit', '=', 0),
            ('name', 'ilike', 'UB'),
        ])
        productB_credit_line = self.env['account.move.line'].search([
            ('product_id', '=', self.glass.id),
            ('debit', '=', 0),
            ('name', 'ilike', 'UB'),
        ])
        self.assertEqual(productB_debit_line.account_id, self.account_stock_valuation)
        self.assertEqual(productB_credit_line.account_id, self.account_production)

    def test_mo_overview_comp_different_uom(self):
        """ Test that the overview takes into account the uom of the component in the price computation
        """
        self.screw.uom_id = self.env.ref('uom.product_uom_pack_6')
        self.bom_1.bom_line_ids.filtered(lambda l: l.product_id == self.screw).product_uom_id = self.env.ref('uom.product_uom_unit')
        mo = self._create_mo(self.bom_1, 1)
        overview_values = self.env['report.mrp.report_mo_overview'].get_report_values(mo.id)
        self.assertEqual(round(overview_values['data']['summary']['mo_cost'], 2), 677.08, "718.75 - 50 + 50/6")
        mo.button_mark_done()
        overview_values = self.env['report.mrp.report_mo_overview'].get_report_values(mo.id)
        self.assertEqual(round(overview_values['data']['summary']['mo_cost'], 2), 677.08)

    def test_mrp_user_without_account_permissions_can_create_bom(self):
        mrp_user = new_test_user(self.env, 'temp_mrp_user', 'mrp.group_mrp_user')
        mo_1 = self._create_mo(self.bom_1, 1)
        mo_1.with_user(mrp_user).button_mark_done()


class TestMrpAccountWorkorder(TestBomPriceOperationCommon):

    def test_01_compute_price_operation_cost(self):
        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        # Total cost of Dining Table = (550) + Total cost of operations (321.25) = 871.25
        # byproduct have 1%+12% of cost share so the final cost is 757.99
        self.assertEqual(float_round(self.dining_table.standard_price, precision_digits=2), 757.99)
        self.Product.browse([self.dining_table.id, self.table_head.id]).action_bom_cost()
        # Total cost of Dining Table = (718.75) + Total cost of all operations (321.25 + 25.52) = 1065.52
        # byproduct have 1%+12% of cost share so the final cost is 927
        self.assertEqual(float_compare(self.dining_table.standard_price, 927, precision_digits=2), 0)

    def test_labor_cost_posting_is_not_rounded_incorrectly(self):
        """ Test to ensure that labor costs are posted accurately without rounding errors."""
        # Build
        self.glass.qty_available = 1
        self.workcenter.costs_hour = 0.01
        production = self._create_mo(self.bom_1, 1)
        production.qty_producing = 1
        workorder = production.workorder_ids
        workorder.duration = 30.2
        workorder.time_ids.write({'duration': 30.2})

        production.move_raw_ids.picked = True
        production.button_mark_done()

        self.assertEqual(production.workorder_ids.mapped('time_ids').mapped('account_move_line_id').mapped('credit'), [
            0.06,
        ])

    def test_02_compute_byproduct_price(self):
        """Test BoM cost when byproducts with cost share"""

        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.assertEqual(self.scrap_wood.standard_price, 30, "Initial price of the By-Product should be 30")
        # bom price is 871.25. Byproduct cost share is 12%+1% = 13% -> 113.26 for 8+12 units -> 5.66
        self.scrap_wood.button_bom_cost()
        self.assertAlmostEqual(self.scrap_wood.standard_price, 5.663125, "After computing price from BoM price should be 20.63")

    def test_wip_accounting_00(self):
        """ Test that posting a WIP accounting entry works as expected.
        WIP MO = MO with some time completed on WOs and/or 'consumed' components
        """
        self.glass.qty_available = 2
        mo = self._create_mo(self.bom_1, 1, confirm=False)

        # post a WIP for an invalid MO, i.e. draft/cancelled/done results in a "Manual Entry"
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.save().confirm()
        wip_manual_entry1 = self.env['account.move'].search([('ref', 'ilike', 'WIP - Manual Entry')])
        self.assertEqual(len(wip_manual_entry1), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_manual_entry1[0].wip_production_count, 0, "Non-WIP MOs shouldn't be linked to manual entry")
        self.assertEqual(len(wip_manual_entry1.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_manual_entry1.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
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
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
        ])

        # WO time completed + components consumed
        mo_form = Form(mo)
        mo_form.qty_producing = mo.product_qty
        mo = mo_form.save()
        now = fields.Datetime.now()
        workorder = mo.workorder_ids[0]
        self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': self.workcenter.id,
            'workorder_id': workorder.id,
            'date_start': now - timedelta(hours=1),
            'date_end': now,
            'loss_id': self.env.ref('mrp.block_reason7').id,
        })
        workorder.button_finish()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': [mo.id]}))
        wizard.save().confirm()
        wip_entries1 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', wip_empty_entries.ids)])
        self.assertEqual(len(wip_entries1), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal")
        self.assertEqual(wip_entries1[0].wip_production_count, 1, "WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries1.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = sum(m.product_qty * m.product_id.standard_price for m in mo.move_raw_ids)
        self.assertRecordValues(wip_entries1.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': total_component_price, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 100.0 + total_component_price},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])

        # Multi-records case
        previous_wip_ids = wip_entries1.ids + wip_empty_entries.ids
        mo_2 = self._create_mo(self.bom_1, 1, confirm=False)
        mos = (mo | mo_2)

        # Draft MOs should be ignored when selecting multiple MOs
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries2 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries2), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for 1 MO")
        self.assertTrue(mo_2.name not in wip_entries2[0].ref, "Draft MO should be completely disregarded by wizard")
        self.assertEqual(wip_entries2[0].wip_production_count, 1, "Only WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries2.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        self.assertRecordValues(wip_entries2.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': total_component_price, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 100.0 + total_component_price},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])
        previous_wip_ids += wip_entries2.ids

        # MOs' WIP amounts should be aggregated
        mo_2.action_confirm()
        mo_2.qty_producing = mo_2.product_qty
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries3 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries3), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for both MOs")
        self.assertTrue(mo_2.name in wip_entries3[0].ref, "Both MOs should have been considered")
        self.assertEqual(wip_entries3[0].wip_production_count, 2, "Both WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries3.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = sum(m.quantity * m.product_id.standard_price for m in mo_2.move_raw_ids)
        self.assertRecordValues(wip_entries3.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': total_component_price, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 100.0 + total_component_price},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 100.0 + total_component_price, 'credit': 0.0},
        ])
        previous_wip_ids += wip_entries3.ids

        # Done MO should be ignored
        mo_2.move_raw_ids.picked = True
        mo_2.button_mark_done()
        wizard = Form(self.env['mrp.account.wip.accounting'].with_context({'active_ids': mos.ids}))
        wizard.save().confirm()
        wip_entries4 = self.env['account.move'].search([('ref', 'ilike', 'WIP - ' + mo.name), ('id', 'not in', previous_wip_ids)])
        self.assertEqual(len(wip_entries4), 2, "Should be 2 journal entries: 1 for the WIP accounting + 1 for its reversal, for 1 MO")
        self.assertTrue(mo_2.name not in wip_entries4[0].ref, "Done MO should be completely disregarded by wizard")
        self.assertEqual(wip_entries4[0].wip_production_count, 1, "Only WIP MOs should be linked to entry")
        self.assertEqual(len(wip_entries4.line_ids), 6, "Should be 3 lines per journal entry: 1 for 'Component Value', 1 for '(WO) overhead', 1 for WIP")
        total_component_price = sum(m.product_qty * m.product_id.standard_price for m in mo.move_raw_ids)
        self.assertRecordValues(wip_entries4.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': total_component_price, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 100.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 100.0 + total_component_price},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': total_component_price},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 100.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 100.0 + total_component_price, 'credit': 0.0},
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
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_overhead_account_id.id, 'debit': 0.0, 'credit': 0.0},
            {'account_id': self.env.company.account_production_wip_account_id.id, 'debit': 0.0, 'credit': 0.0},
        ])

    def test_labor_cost_balancing(self):
        """ When the workcenter_cost ends up like x.xx5 with a currency rounding of 0.01,
        the valuation 'account.move' was unbalanced.
        This happened because the credit value rounded up twice, and instead of having -0.005 + 0.005 => 0,
        we had -0 + 0.01 => +0.01, which made the credit differ from the debit by 0.01.
        This test ensures that if the workcenter_cost is rounded to 0.01, then the credit value is correctly
        decremented by 0.01.
        """
        # Build
        self.dining_table.categ_id = self.category_avco_auto
        self.glass.qty_available = 1
        production = self._create_mo(self.bom_1, 1)
        production.qty_producing = 1
        workorder = production.workorder_ids
        workorder.duration = 0.03  # ~= 2 seconds (1.8 seconds exactly)
        workorder.time_ids.write({'duration': 0.03})  # Ensure that the duration is correct
        self.assertEqual(workorder._cal_cost(), (len(workorder) * 2 / 3600) * 100)  # 2 seconds at $100/h

        production.move_raw_ids.picked = True
        production.button_mark_done()

        # value = finished product value + labour cost - byproduct cost share
        account_move = production.move_finished_ids.account_move_id
        self.assertRecordValues(account_move.line_ids, [
            {'credit': 625.6, 'debit': 0.00},  # Credit Line
            {'credit': 0.00, 'debit': 625.6},  # Debit Line
        ])
        labour_move = workorder.time_ids.account_move_line_id.move_id
        # sum of workorder costs but rounded at company currency
        self.assertRecordValues(labour_move.line_ids, [
            {'credit': 0.36, 'debit': 0.00},
            {'credit': 0.00, 'debit': 0.36},
        ])

    def test_labor_cost_over_consumption(self):
        """ Test the labour accounting entries creation is independent of consumption variation"""
        self.glass.qty_available = 1
        production = self._create_mo(self.bom_1, 1)
        production.workorder_ids.duration = 60

        production.qty_producing = 1

        # overconsume one component to get a warning wizard
        production.move_raw_ids[0].quantity += 2

        production.move_raw_ids.picked = True
        action = production.button_mark_done()
        consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context'])).save()
        consumption_warning.action_confirm()

        mo_aml = self.env['account.move.line'].search([('name', 'like', production.name)])
        labour = 600
        compo_price = 718.75 + 2 * 200
        cost_share = 0.13
        self.assertEqual(len(mo_aml), 6, "2 Labour + 2 finished product + 7 for the components")
        self.assertRecordValues(mo_aml, [
            {'name': production.name + ' - Labour', 'debit': 0.0, 'credit': labour},
            {'name': production.name + ' - Labour', 'debit': labour, 'credit': 0.0},
            {'name': production.name + ' - ' + self.dining_table.name, 'debit': 0.0, 'credit': (labour + compo_price) * (1 - cost_share)},
            {'name': production.name + ' - ' + self.dining_table.name, 'debit': (labour + compo_price) * (1 - cost_share), 'credit': 0.0},
            {'name': production.name + ' - ' + self.glass.name, 'debit': 0.0, 'credit': 100.0},
            {'name': production.name + ' - ' + self.glass.name, 'debit': 100.0, 'credit': 0.0},
        ])

    def test_estimated_cost_valuation(self):
        """ Test that operations with 'estimated' cost correctly compute the cost.
        The cost should be equal to workcenter.costs_hour * workorder.duration_expected. """
        mo = self._create_mo(self.bom_1, 1)
        self.bom_1.operation_ids.cost_mode = 'actual'
        mo.workorder_ids.duration = 60
        self.assertEqual(mo.workorder_ids._cal_cost(), 600)

        # Cost should stay the same for a done MO if nothing else is changed
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.workcenter.costs_hour = 333
        self.assertEqual(mo.workorder_ids._cal_cost(), 600)

    def test_mo_without_finished_moves(self):
        """Test that a MO without finished moves can post inventory and be completed."""
        mo = self._create_mo(self.bom_1, 1)
        workorder = mo.workorder_ids
        workorder.duration = 60
        self.assertEqual(workorder._cal_cost(), 600)
        # Simulate missing finished moves
        mo.move_finished_ids.unlink()
        # Post inventory and complete MO
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

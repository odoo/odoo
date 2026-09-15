from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_jp_stock.tests.common import TestTotalAverageCostCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTotalAverageCostMrp(TestTotalAverageCostCommon):
    def _create_mo(self, qty=3, byproduct_cost_share=None, operation=None):
        component = self.env['product.product'].create({
            'name': 'JP Component', 'categ_id': self.category.id,
            'standard_price': 20, 'is_storable': True,
        })
        self._create_move(10, 25, self.today, self.supplier_loc, self.stock_loc, product=component)
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal',
        })
        self.env['mrp.bom.line'].create({'bom_id': bom.id, 'product_id': component.id, 'product_qty': 2})
        byproduct = False
        if byproduct_cost_share is not None:
            byproduct = self.env['product.product'].create({
                'name': 'JP Byproduct', 'categ_id': self.category.id, 'is_storable': True,
            })
            self.env['mrp.bom.byproduct'].create({
                'bom_id': bom.id, 'product_id': byproduct.id,
                'product_qty': 1, 'cost_share': byproduct_cost_share,
            })
        if operation:
            self.env['mrp.routing.workcenter'].create({
                'bom_id': bom.id, 'name': 'JP Operation', **operation,
            })
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id, 'product_qty': qty, 'bom_id': bom.id,
            'location_src_id': self.stock_loc.id, 'location_dest_id': self.stock_loc.id,
        })
        mo.action_confirm()
        return mo, byproduct

    def _finish_mo(self, mo):
        mo.button_mark_done()
        mo.move_raw_ids.date = fields.Datetime.to_datetime(self.today)
        mo.move_finished_ids.date = fields.Datetime.to_datetime(self.today)
        # the labour is logged at the wall clock, which is not the evaluated period
        self._log_work_at(mo, self.today)

    def _log_work_at(self, mo, date):
        """Move the time the work orders logged to ``date``, keeping how long it took."""
        for entry in mo.workorder_ids.time_ids:
            worked = entry.date_end - entry.date_start
            entry.date_start = fields.Datetime.to_datetime(date)
            entry.date_end = entry.date_start + worked

    def test_byproduct_recycled_into_its_own_component_refused(self):
        ingot = self.env['product.product'].create({
            'name': 'JP Ingot', 'categ_id': self.category.id, 'is_storable': True, 'standard_price': 100,
        })
        casting = self.env['product.product'].create({
            'name': 'JP Casting', 'categ_id': self.category.id, 'is_storable': True,
        })
        self._create_move(10, 100, self.today, self.supplier_loc, self.stock_loc, product=ingot)
        craft_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal',
        })
        self.env['mrp.bom.line'].create({'bom_id': craft_bom.id, 'product_id': ingot.id, 'product_qty': 1})
        # the casting the craft gives off is melted back into the ingot it came from
        self.env['mrp.bom.byproduct'].create({
            'bom_id': craft_bom.id, 'product_id': casting.id, 'product_qty': 1, 'cost_share': 20,
        })
        ingot_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': ingot.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal',
        })
        self.env['mrp.bom.line'].create({'bom_id': ingot_bom.id, 'product_id': casting.id, 'product_qty': 1})
        for product, bom in ((self.product, craft_bom), (ingot, ingot_bom)):
            mo = self.env['mrp.production'].create({
                'product_id': product.id, 'product_qty': 1, 'bom_id': bom.id,
                'location_src_id': self.stock_loc.id, 'location_dest_id': self.stock_loc.id,
            })
            mo.action_confirm()
            self._finish_mo(mo)
        with self.assertRaises(UserError):
            self._run_category_wizard()

    def test_manufacturing_output_real_mo(self):
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        # a second output move on the same order must not re-count its components
        self._create_move(1, 0, self.today, self.product.property_stock_production, self.stock_loc, production_id=mo.id)
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 150 / 4, places=2)
        self.assertEqual(action['params']['type'], 'success')

    def test_output_split_across_periods_not_double_counted(self):
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        tomorrow = self.today + timedelta(days=1)
        self._create_move(1, 0, tomorrow, self.product.property_stock_production, self.stock_loc, production_id=mo.id)
        self._run_category_wizard(date_from=self.today, date_to=self.today)
        self.assertAlmostEqual(self.product.standard_price, 150 / 4, places=2)
        self._run_category_wizard(date_from=tomorrow, date_to=tomorrow)
        self.assertAlmostEqual(self.product.standard_price, 150 / 4, places=2)

    def test_evaluating_the_same_period_twice_is_stable(self):
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 150 / 3, places=2)
        # the second run reads the values the first one corrected, so it must not move
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 150 / 3, places=2)
        self.assertEqual(action['params']['type'], 'info')

    def test_each_level_reads_the_corrected_cost_of_the_one_below(self):
        def assemble(product, component, component_qty=2):
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': product.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal',
            })
            self.env['mrp.bom.line'].create({
                'bom_id': bom.id, 'product_id': component.id, 'product_qty': component_qty,
            })
            mo = self.env['mrp.production'].create({
                'product_id': product.id, 'product_qty': 1, 'bom_id': bom.id,
                'location_src_id': self.stock_loc.id, 'location_dest_id': self.stock_loc.id,
            })
            mo.action_confirm()
            self._finish_mo(mo)

        component = self.env['product.product'].create({
            'name': 'JP Deep Component', 'categ_id': self.category.id,
            'standard_price': 20, 'is_storable': True,
        })
        # the evaluation itself takes the component from 20 to 25
        self._create_move(10, 25, self.today, self.supplier_loc, self.stock_loc, product=component)
        subassembly = self.env['product.product'].create({
            'name': 'JP Subassembly', 'categ_id': self.category.id,
            'standard_price': 5, 'is_storable': True,
        })
        assemble(subassembly, component)
        assemble(self.product, subassembly, component_qty=1)
        self._run_category_wizard()
        # each order is valued on what the level below was corrected to: 2 components at 25
        self.assertAlmostEqual(component.standard_price, 250 / 10, places=2)
        self.assertAlmostEqual(subassembly.standard_price, 2 * 25, places=2)
        self.assertAlmostEqual(self.product.standard_price, 2 * 25, places=2)

    def test_byproduct_takes_its_cost_share(self):
        mo, byproduct = self._create_mo(byproduct_cost_share=25)
        self._finish_mo(mo)
        self._run_category_wizard()
        # 6 components at 25 is 150, of which the by-product's BoM claims a quarter
        self.assertAlmostEqual(self.product.standard_price, 150 * 0.75 / 3, places=2)
        self.assertAlmostEqual(byproduct.standard_price, 150 * 0.25 / 3, places=2)

    def test_extra_cost_is_part_of_the_manufacturing_cost(self):
        mo, _byproduct = self._create_mo()
        mo.extra_cost = 5
        self._finish_mo(mo)
        self._run_category_wizard()
        # 法人税法施行令 32条1項2号 counts the 経費 alongside the materials
        self.assertAlmostEqual(self.product.standard_price, (150 + 3 * 5) / 3, places=2)

    def test_manual_correction_on_the_output_outranks_the_order(self):
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        # someone stated what the goods finally cost, which outranks the 製造原価
        # the order adds up, the same way it outranks a bill on a receipt
        mo.move_finished_ids.value_manual = 3 * 90
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 90, places=2)

    def test_landed_cost_on_the_order_is_part_of_the_manufacturing_cost(self):
        self.ensure_installed('mrp_landed_costs')
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        freight = self.env['product.product'].create({
            'name': 'JP Freight', 'type': 'service', 'landed_cost_ok': True,
        })
        landed_cost = self.env['stock.landed.cost'].create({  # noqa: OLS03001
            'date': self.today,
            'target_model': 'manufacturing',
            'mrp_production_ids': [(6, 0, mo.ids)],
            'cost_lines': [(0, 0, {
                'product_id': freight.id, 'price_unit': 300, 'split_method': 'equal',
            })],
        })
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()
        self._run_category_wizard()
        # 法人税法施行令 32条1項2号 counts what it cost to bring the goods in whether
        # they were bought or made, so the freight of an order belongs in its 製造原価
        self.assertAlmostEqual(self.product.standard_price, (150 + 300) / 3, places=2)

    def test_workcenter_cost_is_part_of_the_manufacturing_cost(self):
        workcenter = self.env['mrp.workcenter'].create({'name': 'JP Workcenter', 'costs_hour': 60})
        mo, _byproduct = self._create_mo(operation={
            'workcenter_id': workcenter.id, 'time_cycle_manual': 60,
        })
        self._finish_mo(mo)
        self._run_category_wizard()
        # 労務費 belongs in the cost of what was produced
        self.assertAlmostEqual(self.product.standard_price, (150 + 3 * 60) / 3, places=2)

    def test_workcenter_time_after_the_period_is_not_counted(self):
        workcenter = self.env['mrp.workcenter'].create({'name': 'JP Workcenter', 'costs_hour': 60})
        mo, _byproduct = self._create_mo(operation={
            'workcenter_id': workcenter.id, 'time_cycle_manual': 60,
        })
        self._finish_mo(mo)
        # the hours are worked the day after the period closes, so it did not pay for them
        self._log_work_at(mo, self.today + timedelta(days=1))
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 150 / 3, places=2)

    def test_byproduct_share_does_not_depend_on_the_selection(self):
        mo, _byproduct = self._create_mo(byproduct_cost_share=25)
        self._finish_mo(mo)
        # only the finished good is evaluated, so its components keep their old 20
        self._run_wizard(product_ids=[self.product.id])
        self.assertAlmostEqual(self.product.standard_price, 120 * 0.75 / 3, places=2)

    def test_unbuild_is_not_an_acquisition(self):
        mo, _byproduct = self._create_mo()
        self._finish_mo(mo)
        component = mo.move_raw_ids.product_id
        unbuild = self.env['mrp.unbuild'].create({
            'mo_id': mo.id,
            'product_id': self.product.id,
            'product_qty': mo.product_qty,
        })
        unbuild.action_unbuild()
        unbuild.produce_line_ids.date = fields.Datetime.to_datetime(self.today)
        self._run_category_wizard()
        self.assertAlmostEqual(component.standard_price, 250 / 10, places=2)

    def _subcontract(self, qty=10, component_price=40, fee=30, component_qty=1):
        """
        Have a subcontractor make ``qty`` of the product out of ``component_qty`` each.

        Returns the order line the fee is charged on, so the test can bill it.
        """
        self.ensure_installed('mrp_subcontracting_purchase')
        subcontractor = self.env['res.partner'].create({'name': 'JP Subcontractor'})
        component = self.env['product.product'].create({
            'name': 'JP Subcontracted Component', 'categ_id': self.category.id,
            'standard_price': 10, 'is_storable': True,
        })
        # the subcontractor consumes out of their own location, so that is where the components go
        self._create_move(
            qty * component_qty, component_price, self.today, self.supplier_loc,
            self.env.company.subcontracting_location_id, product=component,
        )
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id, 'product_qty': 1,
            'type': 'subcontract', 'subcontractor_ids': [(6, 0, subcontractor.ids)],
        })
        self.env['mrp.bom.line'].create({
            'bom_id': bom.id, 'product_id': component.id, 'product_qty': component_qty,
        })
        # a tax belongs to neither the fee nor the components, so keep it out of the arithmetic
        self.product.supplier_taxes_id = False
        order = self.env['purchase.order'].create({'partner_id': subcontractor.id})  # noqa: OLS03001
        line = self.env['purchase.order.line'].create({  # noqa: OLS03001
            'order_id': order.id, 'product_id': self.product.id,
            'product_qty': qty, 'price_unit': fee,
        })
        order.button_confirm()
        receipt = order.picking_ids
        receipt.move_ids.picked = True
        receipt.button_validate()
        production = receipt._get_subcontract_production()
        moves = production.move_raw_ids | production.move_finished_ids | receipt.move_ids
        moves.date = fields.Datetime.to_datetime(self.today)
        return line

    def _bill_subcontractor(self, line, price_unit, qty=None):
        """Post what the subcontractor finally charged, the way it comes after the goods."""
        line.order_id.action_create_invoice()
        bill = line.order_id.invoice_ids
        bill.invoice_date = self.today
        bill.invoice_line_ids.price_unit = price_unit
        if qty is not None:
            bill.invoice_line_ids.quantity = qty
        bill.action_post()
        return bill

    def test_subcontracting_fee_is_read_back_from_the_bill(self):
        line = self._subcontract()
        # the goods arrive before the bill, so the fee the order was marked done with is an estimate
        self._bill_subcontractor(line, 45)
        self._run_category_wizard()
        # 外注加工費 is what the subcontractor charged, not what the order guessed
        self.assertAlmostEqual(self.product.standard_price, (400 + 10 * 45) / 10, places=2)

    def test_subcontracting_fee_falls_back_to_the_order(self):
        self._subcontract()
        self._run_category_wizard()
        # nothing is billed yet, so what the order charges is the only price there is
        self.assertAlmostEqual(self.product.standard_price, (400 + 10 * 30) / 10, places=2)

    def test_partly_billed_subcontracting_fee_is_blended(self):
        line = self._subcontract()
        self._bill_subcontractor(line, 45, qty=4)
        self._run_category_wizard()
        # what is billed is priced at the bill and the rest at the order, as on any receipt
        self.assertAlmostEqual(self.product.standard_price, (400 + 4 * 45 + 6 * 30) / 10, places=2)

    def test_a_bill_reaches_a_period_already_evaluated(self):
        """The scenario the PO reproduced: the fee is billed after the period was evaluated."""
        line = self._subcontract(qty=1, component_qty=5, component_price=100, fee=550)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 5 * 100 + 550, places=2)
        # the bill lands inside the period, days after the goods and the first evaluation
        self._bill_subcontractor(line, 600)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 5 * 100 + 600, places=2)

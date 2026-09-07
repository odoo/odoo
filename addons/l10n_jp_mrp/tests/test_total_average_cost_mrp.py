from datetime import timedelta

from odoo import fields
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

    def test_workcenter_cost_is_part_of_the_manufacturing_cost(self):
        workcenter = self.env['mrp.workcenter'].create({'name': 'JP Workcenter', 'costs_hour': 60})
        mo, _byproduct = self._create_mo(operation={
            'workcenter_id': workcenter.id, 'time_cycle_manual': 60,
        })
        self._finish_mo(mo)
        self._run_category_wizard()
        # 労務費 belongs in the cost of what was produced
        self.assertAlmostEqual(self.product.standard_price, (150 + 3 * 60) / 3, places=2)

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
        # the components come back because an issue was reversed, not because they
        # were acquired, so they must not dilute the average
        self.assertAlmostEqual(component.standard_price, 250 / 10, places=2)

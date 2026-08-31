from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_jp_stock.tests.common import TestTotalAverageCostCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTotalAverageCostMrp(TestTotalAverageCostCommon):
    def test_manufacturing_output_real_mo(self):
        component = self.env['product.product'].create({'name': 'JP Component', 'categ_id': self.category.id, 'standard_price': 20, 'is_storable': True})
        self._create_move(10, 25, self.today, self.supplier_loc, self.stock_loc, product=component)
        bom = self.env['mrp.bom'].create({'product_tmpl_id': self.product.product_tmpl_id.id, 'product_qty': 1, 'type': 'normal'})
        self.env['mrp.bom.line'].create({'bom_id': bom.id, 'product_id': component.id, 'product_qty': 2})
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 3,
            'bom_id': bom.id,
            'location_src_id': self.stock_loc.id,
            'location_dest_id': self.stock_loc.id,
        })
        mo.action_confirm()
        mo.button_mark_done()
        mo.move_raw_ids.date = fields.Datetime.to_datetime(self.today)
        mo.move_finished_ids.date = fields.Datetime.to_datetime(self.today)
        # the same MO must not be counted twice
        extra_output = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'location_id': self.product.property_stock_production.id,
            'location_dest_id': self.stock_loc.id,
            'production_id': mo.id,
            'date': self.today,
        })
        extra_output._action_confirm()
        extra_output._action_assign()
        extra_output.picked = True
        extra_output._action_done()
        extra_output.date = fields.Datetime.to_datetime(self.today)
        action = self._run_category_wizard()
        # output valued at consumed materials ONCE (6 components at cost 20),
        # spread over all 4 produced units
        self.assertAlmostEqual(self.product.standard_price, 120 / 4, places=2)
        self.assertEqual(action['params']['type'], 'success')

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

    def test_byproduct_takes_its_cost_share(self):
        mo, byproduct = self._create_mo(byproduct_cost_share=25)
        self._finish_mo(mo)
        self._run_category_wizard()
        # 6 components at 20 is 120, of which the by-product's bill of materials claims a quarter
        self.assertAlmostEqual(self.product.standard_price, 90 / 3, places=2)
        self.assertAlmostEqual(byproduct.standard_price, 30 / 3, places=2)

    def test_extra_cost_is_part_of_the_manufacturing_cost(self):
        mo, _byproduct = self._create_mo()
        mo.extra_cost = 5
        self._finish_mo(mo)
        self._run_category_wizard()
        # 法人税法施行令 32条1項2号 counts the 経費 alongside the materials
        self.assertAlmostEqual(self.product.standard_price, (120 + 3 * 5) / 3, places=2)

    def test_work_center_cost_is_part_of_the_manufacturing_cost(self):
        workcenter = self.env['mrp.workcenter'].create({'name': 'JP Work Center', 'costs_hour': 60})
        mo, _byproduct = self._create_mo(operation={
            'workcenter_id': workcenter.id, 'time_cycle_manual': 60,
        })
        self._finish_mo(mo)
        work_center_cost = sum(mo.workorder_ids.mapped('duration_expected')) / 60 * 60
        self.assertGreater(work_center_cost, 0)
        self._run_category_wizard()
        # 労務費 belongs in the cost of what was produced
        self.assertAlmostEqual(self.product.standard_price, (120 + work_center_cost) / 3, places=2)

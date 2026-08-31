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
        raw_value = sum(mo.move_raw_ids.mapped('value'))
        self.assertEqual(raw_value, -6 * 20)
        action = self._run_category_wizard()
        # output valued at consumed materials ONCE (6 components at cost 20),
        # spread over all 4 produced units
        self.assertAlmostEqual(self.product.standard_price, 120 / 4, places=2)
        self.assertEqual(action['params']['type'], 'success')

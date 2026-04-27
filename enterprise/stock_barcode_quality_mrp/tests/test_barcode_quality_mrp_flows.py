# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBarcodeQualityControlMRPClientAction(HttpCase):

    def test_final_product_quality_check_mrp_barcode(self):
        """
        Test quality check on productions created in barcode.
        """
        final_product, component = self.env['product.product'].create([
            {'name': 'Lovely product', 'barcode': 'love724'}, {'name': 'Lovely component'}
        ])
        self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1})]
        })
        quality_points = self.env['quality.point'].create([
            {
                'title': 'check lovely product',
                'measure_on': 'product',
                'product_ids': [Command.link(final_product.id)],
                'picking_type_ids': [Command.link(self.env.ref('stock.warehouse0').manu_type_id.id)],
            },
        ])
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_final_product_quality_check_mrp_barcode', login='admin')

        quality_checks = self.env['quality.check'].search([('point_id', 'in', quality_points.ids)])
        self.assertRecordValues(quality_checks.sorted('title'), [
            {'title': 'check lovely product', 'quality_state': 'pass'},
        ])
        self.assertEqual(quality_checks.production_id.state, "done")

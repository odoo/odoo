from odoo.tests.common import tagged, HttpCase
from odoo import Command

from odoo.addons.quality_control.tests.test_common import TestQualityCommon


@tagged('post_install', '-at_install')
class TestQualityWorksheet(HttpCase, TestQualityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worksheet_template = cls.env['worksheet.template'].create({
            'name': 'Quality worksheet',
            'res_model': 'quality.check',
        })
        cls.receipt_type = cls.env.ref('stock.picking_type_in')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')

    def test_multiple_worksheet_checks(self):
        """ Have a receipt for two product, to trigger quality checks for each product.
            the two worksheet should be opened back to back for completion
        """
        self.env['quality.point'].create({
            'name': 'QP1',
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control_worksheet.test_type_worksheet').id,
            'worksheet_template_id': self.worksheet_template.id,
            'picking_type_ids': [Command.link(self.receipt_type.id)],
            'worksheet_success_conditions': "[('x_passed', '=', True)]",
            'failure_location_ids': [Command.link(self.failure_location.id)]
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.receipt_type.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
        })

        self.env['stock.move'].create([
            {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            },
            {
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            }
        ])
        receipt.action_confirm()
        self.assertEqual(len(receipt.check_ids), 2)
        # launch tour to test the worksheets opening back to back
        action = self.env.ref('stock.action_picking_tree_all')
        action['res_id'] = receipt.id
        action['view_id'] = self.env.ref('stock.view_picking_form')
        url = '/web#action=%s&active_id=%s' % (action.id, receipt.id)
        self.start_tour(url, 'test_multiple_worksheet_checks', login='admin')
        # there should be 3 move lines and 3 checks
        self.assertEqual(len(receipt.move_line_ids), 3)
        self.assertRecordValues(receipt.check_ids, [
            {'quality_state': 'fail', 'product_id': self.product.id, 'qty_line': 1, 'failure_location_id': self.failure_location.id},
            {'quality_state': 'pass', 'product_id': self.product_2.id, 'qty_line': 2, 'failure_location_id': []},
            {'quality_state': 'pass', 'product_id': self.product.id, 'qty_line': 1, 'failure_location_id': []},
        ])

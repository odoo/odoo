# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import fields
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.addons.purchase_stock.models.purchase_order_line import PurchaseOrderLine
from odoo.tests.common import tagged

from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestUninstallPurchaseStock(PurchaseTestCommon):
    def test_qty_received_method(self):
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'state': 'done',
            'line_ids': [fields.Command.create({
                'product_id': self.product_1.id,
            })],
        })
        order_line = purchase_order.line_ids
        stock_move = order_line.move_ids

        self.assertEqual(order_line.product_id.is_storable, True)

        stock_move.quantity = 1
        stock_move.picked = True
        stock_move.picking_id.button_validate()

        self.assertEqual(purchase_order.line_ids.qty_transferred, 1)

        stock_moves_option = self.env['ir.model.fields.selection'].search([
            ('field_id.model', '=', 'purchase.order.line'),
            ('field_id.name', '=', 'qty_transferred_method'),
            ('value', '=', 'stock_move'),
        ])

        original_compute = PurchaseOrderLine._compute_qty_transferred
        def _compute_qty_transferred(records):
            records.read()
            with self.assertQueryCount(0):
                original_compute(records)
                records.flush_recordset()

        with patch.object(PurchaseOrderLine, '_compute_qty_transferred', _compute_qty_transferred):
            stock_moves_option.sudo().with_context(**{
                MODULE_UNINSTALL_FLAG: True
            }).unlink()

        # After uninstalling stock_move option, the computed method value persists
        self.assertEqual(order_line.qty_transferred_method, 'stock_move')
        self.assertEqual(order_line.qty_transferred, 1)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase


class TestCancelOriginRestore(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.picking_type_in = cls.env.ref('stock.picking_type_in')
        cls.picking_type_internal = cls.env.ref('stock.picking_type_internal')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Cancel Origin Restore Product',
            'type': 'product',
        })

    def test_cancel_from_mo_keeps_non_cancelled_origins(self):
        move_orig_open = self.env['stock.move'].create({
            'name': 'origin open',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'propagate_cancel': False,
        })
        move_orig_cancel = self.env['stock.move'].create({
            'name': 'origin cancel',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'propagate_cancel': False,
        })
        move_dest = self.env['stock.move'].create({
            'name': 'destination',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'procure_method': 'make_to_order',
            'move_orig_ids': [
                Command.link(move_orig_open.id),
                Command.link(move_orig_cancel.id),
            ],
        })
        (move_orig_open | move_orig_cancel | move_dest)._action_confirm()

        move_orig_cancel._action_cancel()
        self.assertEqual(move_orig_cancel.state, 'cancel')
        self.assertEqual(move_dest.move_orig_ids, move_orig_open | move_orig_cancel)

        move_dest.with_context(cancel_from_mo=True)._action_cancel()
        self.assertEqual(move_dest.state, 'cancel')
        self.assertEqual(move_dest.procure_method, 'make_to_stock')
        self.assertEqual(move_dest.move_orig_ids, move_orig_open)
        self.assertNotEqual(move_orig_open.state, 'cancel')

    def test_cancel_without_flag_clears_origins(self):
        move_orig = self.env['stock.move'].create({
            'name': 'origin',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'propagate_cancel': False,
        })
        move_dest = self.env['stock.move'].create({
            'name': 'destination',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'procure_method': 'make_to_order',
            'move_orig_ids': [Command.link(move_orig.id)],
        })
        (move_orig | move_dest)._action_confirm()
        move_dest._action_cancel()
        self.assertEqual(move_dest.state, 'cancel')
        self.assertFalse(move_dest.move_orig_ids)

    def test_action_done_cancel_backorder_keeps_cancelled_origins_for_traceability(self):
        receipt_move = self.env['stock.move'].create({
            'name': 'receipt',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'propagate_cancel': True,
        })
        downstream_move = self.env['stock.move'].create({
            'name': 'downstream',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_internal.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'procure_method': 'make_to_order',
            'move_orig_ids': [Command.link(receipt_move.id)],
        })
        (receipt_move | downstream_move)._action_confirm()

        receipt_move.with_context(cancel_backorder=True)._action_done(cancel_backorder=True)

        self.assertEqual(receipt_move.state, 'cancel')
        self.assertEqual(downstream_move.state, 'cancel')
        self.assertEqual(downstream_move.procure_method, 'make_to_stock')
        self.assertEqual(downstream_move.move_orig_ids, receipt_move)
        self.assertEqual(receipt_move.move_dest_ids, downstream_move)

    def test_action_done_cancel_backorder_relinks_receipt_dest_when_propagate_is_false(self):
        receipt_move = self.env['stock.move'].create({
            'name': 'receipt mts',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'propagate_cancel': False,
        })
        downstream_move = self.env['stock.move'].create({
            'name': 'downstream mts',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_internal.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'procure_method': 'make_to_order',
            'move_orig_ids': [Command.link(receipt_move.id)],
        })
        (receipt_move | downstream_move)._action_confirm()

        receipt_move.with_context(cancel_backorder=True)._action_done(cancel_backorder=True)

        self.assertEqual(receipt_move.state, 'cancel')
        self.assertEqual(downstream_move.procure_method, 'make_to_stock')
        self.assertEqual(downstream_move.move_orig_ids, receipt_move)
        self.assertEqual(receipt_move.move_dest_ids, downstream_move)
        self.assertNotEqual(downstream_move.state, 'cancel')

    def test_action_done_direct_cancel_backorder_argument_keeps_receipt_dest(self):
        receipt_move = self.env['stock.move'].create({
            'name': 'receipt direct arg',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'propagate_cancel': True,
        })
        downstream_move = self.env['stock.move'].create({
            'name': 'downstream direct arg',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_internal.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'procure_method': 'make_to_order',
            'move_orig_ids': [Command.link(receipt_move.id)],
        })
        (receipt_move | downstream_move)._action_confirm()

        # Param cancels the move; context enables origin restore (same as picking No Backorder).
        receipt_move.with_context(cancel_backorder=True)._action_done(cancel_backorder=True)

        self.assertEqual(receipt_move.state, 'cancel')
        self.assertEqual(downstream_move.state, 'cancel')
        self.assertEqual(downstream_move.move_orig_ids, receipt_move)
        self.assertEqual(receipt_move.move_dest_ids, downstream_move)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):

    def setUp(self):
        super().setUp()

        self.component01 = self.env['product.product'].create({
            'name': 'Compo 01',
            'type': 'product',
            'barcode': 'compo01',
        })
        self.component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'type': 'product',
            'barcode': 'compo02',
        })
        self.component_lot = self.env['product.product'].create({
            'name': 'Compo Lot',
            'type': 'product',
            'barcode': 'compo_lot',
            'tracking': 'lot',
        })

        self.simple_kit = self.env['product.product'].create({
            'name': 'Simple Kit',
            'type': 'product',
            'barcode': 'simple_kit',
        })
        self.kit_lot = self.env['product.product'].create({
            'name': 'Kit Lot',
            'type': 'product',
            'barcode': 'kit_lot',
        })

        self.bom_kit_lot = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_lot.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': self.component_lot.id, 'product_qty': 1.0}),
            ],
        })
        self.bom_simple_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': self.simple_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': self.component02.id, 'product_qty': 1.0}),
            ],
        })

    def test_immediate_receipt_kit_from_scratch_with_tracked_compo(self):
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_immediate_receipt_kit_from_scratch_with_tracked_compo', login='admin', timeout=180)

        self.assertRecordValues(receipt_picking.move_ids.move_line_ids, [
            {'product_id': self.component01.id, 'qty_done': 3.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component_lot.id, 'qty_done': 3.0, 'lot_name': 'super_lot', 'state': 'done'},
            {'product_id': self.component01.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component02.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
        ])

    def test_planned_receipt_kit_from_scratch_with_tracked_compo(self):
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_planned_receipt_kit_from_scratch_with_tracked_compo', login='admin', timeout=180)

        self.assertRecordValues(receipt_picking.move_ids.move_line_ids, [
            {'product_id': self.component01.id, 'qty_done': 3.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component_lot.id, 'qty_done': 3.0, 'lot_name': 'super_lot', 'state': 'done'},
            {'product_id': self.component01.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component02.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
        ])

    def test_picking_product_with_kit_and_packaging(self):
        """ A picking with a move for a product with a kit BOM and packaging can be processed
        in Barcode
        """
        self.clean_access_rights()

        packaging = self.env['product.packaging'].create({
            'name': 'test packaging',
            'qty': 1,
            'product_id': self.simple_kit.id,
        })

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_internal.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [(0, 0, {
                'name': 'test_picking_product_with_packaging stock move',
                'product_id': self.simple_kit.id,
                'product_uom_qty': 1.0,
                'product_uom': self.simple_kit.uom_id.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
                'product_packaging_id': packaging.id,
            })],
        })
        picking.action_confirm()

        create_vals = []
        for stock_move, component in zip(picking.move_ids, picking.move_ids.mapped('product_id')):
            create_vals.append({
                'product_id': component.id,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
                'quantity': 1.0,
            })

        self.env['stock.move.line'].create(create_vals)

        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_picking_product_with_kit_and_packaging', login='admin', timeout=180)
        self.assertEqual(picking.state, 'done')

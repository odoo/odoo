# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import Command
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSubcontractingBarcodeClientAction(TestBarcodeClientAction):
    def setUp(self):
        super(TestSubcontractingBarcodeClientAction, self).setUp()

        self.subcontractor_partner = self.env['res.partner'].create({
            'name': 'Pastry Cook',
            'company_id': self.env.ref('base.main_company').id
        })
        self.subcontracted_product = self.env['product.product'].create({
            'name': 'Chocolate Eclairs',
            'type': 'product',
            'barcode': 'product_subcontracted',
        })
        self.subcontracted_component = self.env['product.product'].create({
            'name': 'Chocolate',
            'type': 'product',
        })
        self.bom = self.env['mrp.bom'].create({
            'type': 'subcontract',
            'consumption': 'strict',
            'subcontractor_ids': [Command.link(self.subcontractor_partner.id)],
            'product_tmpl_id': self.subcontracted_product.product_tmpl_id.id,
            'bom_line_ids': [Command.create({
                'product_id': self.subcontracted_component.id,
                'product_qty': 1,
            })]
        })

    def test_receipt_classic_subcontracted_product(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        receipt_picking = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': 'test_receipt_classic_subcontracted_product',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.subcontracted_product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_classic_subcontracted_product', login='admin', timeout=180)

        self.assertEqual(receipt_picking.state, 'done')
        self.assertEqual(receipt_picking.move_ids.quantity, 2)
        self.assertTrue(receipt_picking.move_line_ids.filtered(lambda ml: ml.location_dest_id == self.shelf1))
        self.assertTrue(receipt_picking.move_line_ids.filtered(lambda ml: ml.location_dest_id == self.shelf2))
        sub_order = self.env['mrp.production'].search([('product_id', '=', self.subcontracted_product.id)])
        self.assertEqual(len(sub_order), 2)
        self.assertEqual(sub_order.mapped('state'), ['done', 'done'])

    def test_receipt_tracked_subcontracted_product(self):
        self.clean_access_rights()
        self.subcontracted_component.tracking = 'lot'
        lot_id = self.env['stock.lot'].create({
            'product_id': self.subcontracted_component.id,
            'company_id': self.env.ref('base.main_company').id,
            'name': 'C01',
        })
        subcontract_location = self.subcontractor_partner.property_stock_subcontractor
        self.env['stock.quant']._update_available_quantity(self.subcontracted_component, subcontract_location, 5, lot_id=lot_id)

        receipt_picking = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': 'test_receipt_classic_subcontracted_product',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.subcontracted_product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_tracked_subcontracted_product', login='admin', timeout=180)
        self.assertEqual(receipt_picking.state, 'done')
        self.assertEqual(receipt_picking.move_ids.quantity, 5)

    def test_receipt_flexible_subcontracted_product(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.bom.consumption = 'flexible'  # To able to record flexible component
        receipt_picking = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': 'test_receipt_classic_subcontracted_product',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.subcontracted_product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_flexible_subcontracted_product', login='admin', timeout=180)

        self.assertEqual(receipt_picking.state, 'done')
        self.assertEqual(receipt_picking.move_ids.quantity, 1)
        sub_order = self.env['mrp.production'].search([('product_id', '=', self.subcontracted_product.id)])
        self.assertEqual(len(sub_order), 1)
        self.assertEqual(sub_order.state, 'done')
        self.assertEqual(sub_order.move_raw_ids.quantity, 2)  # because we record more than expected

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


@tagged('post_install', '-at_install')
class TestSubcontractingDropshippingMps(TestMrpSubcontractingCommon):
    def setUp(self):
        super().setUp()
        if 'mrp.production.schedule' not in self.env:
            self.skipTest('`mps` is not installed')

    def test_subcontracting_dropshipping_mps(self):
        subcontract_location = self.env.company.subcontracting_location_id
        sub_location = self.env['stock.location'].create({
            'name': 'Super Location',
            'location_id': subcontract_location.id,
        })

        #create a new route
        outsourcing_sl = self.env['stock.route'].create({
            'name': 'Outsourcing to SL',
        })

        self.env['stock.rule'].create([{
            'name': 'Rule 1',
            'action': 'buy',
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_dest_id': sub_location.id,
            'route_id': outsourcing_sl.id,
        }, {
            'name': 'Rule 2',
            'action': 'pull',
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_src_id': sub_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'procure_method': 'make_to_order',
            'route_id': outsourcing_sl.id
        }, {
            'name': 'Rule 3',
            'action': 'pull',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_src_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'procure_method': 'mts_else_mto',
            'route_id': outsourcing_sl.id
        }
        ])

        subcontractor = self.env['res.partner'].create([
            {'name': 'SuperSubcontractor', 'property_stock_subcontractor': sub_location},
        ])

        dropship_subcontractor_route = self.env['stock.route'].search([('name', '=', 'Dropship Subcontractor on Order')])

        p_finished, p_compo = self.env['product.product'].create([{
            'name': 'Finished Product',
            'type': 'product',
            'route_ids': [(6, 0, [outsourcing_sl.id])],
            'seller_ids': [(0, 0, {'partner_id': subcontractor.id})],
        }, {
            'name': 'Component',
            'route_ids': [(6, 0, [dropship_subcontractor_route.id])]
        }])

        self.env['mrp.bom'].create({
            'product_tmpl_id': p_finished.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, subcontractor.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': p_compo.id, 'product_qty': 1}),
            ],
        })

        mps = self.env['mrp.production.schedule'].create({
            'product_id': p_finished.id,
            'warehouse_id': self.warehouse.id,
            'min_to_replenish_qty': 5,
        })
        mps.action_replenish()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', p_finished.id)])
        self.assertTrue(purchase_order_line)
        self.assertEqual(purchase_order_line.product_qty, 5)

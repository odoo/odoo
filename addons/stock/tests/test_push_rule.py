# -*- coding: utf-8 -*-
# © 2017  Cédric Pigeon, Acsone SA/NV (http://www.acsone.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestPushApply(common.TransactionCase):

    def setUp(self):
        super(TestPushApply, self).setUp()
        self.product = self.browse_ref("product.product_product_6")
        self.picking_type = self.env.ref('stock.picking_type_internal')
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.location_shelf = self.browse_ref(
            "stock.stock_location_components")
        self.location1 =  self.env['stock.location'].create({
            'name': 'Location 1',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_stock').id
        })
        self.location2 = self.env['stock.location'].create({
            'name': 'Location 2',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_stock').id
        })
        self.location3 = self.env['stock.location'].create({
            'name': 'Location 3',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_stock').id
        })
        # Create a route with a push rule transferring automatically
        # from location 2 to location 3
        route = self.env['stock.location.route'].create({
             "name": "Test",
             "sequence": 20,
             "product_categ_selectable": False,
             "product_selectable": True,
             "pull_ids": [(0, 0, {
                 'name': "Test",
                 'action': 'move',
                 'location_id': self.location2.id,
                 'warehouse_id': self.env.ref('stock.warehouse0').id,
                 'group_propagation_option': 'propagate',
                 'propagate': True,
                 'picking_type_id': self.picking_type.id,
                 'procure_method': 'make_to_stock',
                 'location_src_id': self.location1.id})],
             "push_ids": [(0, 0, {
                 'name': 'Test',
                 'location_from_id': self.location2.id,
                 'location_dest_id': self.location3.id,
                 'auto': 'transparent',
                 'picking_type_id': self.picking_type.id})]})
        # set route on product
        self.product.route_ids = [
            (4, route.id)]

    def test_push_rule_without_picking(self):
        '''
            - Create a move from location shelf to location 2
            - The stock should be automatically moved on location 3 because of
              the push rule defined on the product's route.
            - Execute the move
        '''
        move = self.env["stock.move"].create({
            'name': "Supply source location for test",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 1,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location2.id,
        })
        move.action_confirm()
        move.action_assign()
        move.action_done()
        quants_in_2 = self.env['stock.quant'].search(
            [('product_id', '=', self.product.id),
             ('location_id', '=', self.location2.id)])
        quants_in_3 = self.env['stock.quant'].search(
            [('product_id', '=', self.product.id),
             ('location_id', '=', self.location3.id)])
        self.assertEqual(len(quants_in_2),
                         0,
                         'No stock should be on location 2')
        self.assertGreater(len(quants_in_3),
                           0, 'Stock should be on location 3')

    def test_push_rule_with_picking(self):
        '''
            - Create a picking
            - Create a move linked to the picking from location shelf to
              location 2
            - Execute the move
            - The stock should be automatically moved on location 3 because of
              the push rule defined on the product's route.
        '''
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location2.id,
        })
        move = self.env["stock.move"].create({
            'picking_id': picking.id,
            'name': "Supply source location for test",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 1,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location2.id,
        })
        move.action_confirm()
        move.action_assign()
        move.action_done()
        quants_in_2 = self.env['stock.quant'].search(
            [('product_id', '=', self.product.id),
             ('location_id', '=', self.location2.id)])
        quants_in_3 = self.env['stock.quant'].search(
            [('product_id', '=', self.product.id),
             ('location_id', '=', self.location3.id)])
        self.assertEqual(len(quants_in_2),
                         0,
                         'No stock should be on location 2')
        self.assertGreater(len(quants_in_3),
                           0, 'Stock should be on location 3')

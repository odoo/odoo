# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo.tests.common import TransactionCase


class TestPackingIn(TransactionCase):

    def setUp(self):
        super(TestPackingIn, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.stock_location.id)], limit=1)
        self.warehouse.write({'reception_steps': 'two_steps'})
        self.input_location = self.warehouse.wh_input_stock_loc_id
        self.vendors_location = self.env.ref('stock.stock_location_suppliers')
        self.two_steps_receive_rule = self.env['stock.rule'].search([
            ('action', '=', 'pull_push'),
            ('location_src_id', '=', self.input_location.id),
            ('location_id', '=', self.stock_location.id),
        ])

        self.receipt_picking_type = self.env.ref('stock.picking_type_in')
        self.internal_picking_type = self.env.ref('stock.picking_type_internal')

        self.productA = self.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        self.productB = self.env['product.product'].create({'name': 'Product B', 'type': 'product'})

        self.shelfA_location = self.env['stock.location'].create({
            'name': 'ShelfA',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.shelfB_location = self.env['stock.location'].create({
            'name': 'ShelfB',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })

        self.putaway = self.env['product.putaway'].create({
            'name': 'WH/Stock'
        })
        self.putaway_productA = self.env['stock.fixed.putaway.strat'].create({
            'putaway_id': self.putaway.id,
            'product_id': self.productA.id,
            'fixed_location_id': self.shelfA_location.id,
            'sequence': 10
        })
        self.putaway_productB = self.env['stock.fixed.putaway.strat'].create({
            'putaway_id': self.putaway.id,
            'product_id': self.productB.id,
            'fixed_location_id': self.shelfB_location.id,
            'sequence': 20,
        })
        self.stock_location.putaway_strategy_id = self.putaway

    def test_put_in_pack_multiple_product_with_putaway(self):
        in_picking, in_move_productA, in_move_productB = self._create_in_picking_with_moves()
        in_picking.action_confirm()
        in_move_productA.move_line_ids.qty_done = 10.0
        in_move_productB.move_line_ids.qty_done = 10.0
        package_productAB = in_picking.put_in_pack()
        # Here the putaway will be applied on the ensuing internal picking
        in_picking.button_validate()
        package_levels = self.env['stock.package_level'].search([
            ('package_id', '=', package_productAB.id),
        ])
        int_picking = self.env['stock.picking'].search([
            ('package_level_ids', 'in', package_levels.ids),
            ('picking_type_id', '=', self.internal_picking_type.id),
        ])
        self.assertEqual(int_picking.location_dest_id, self.stock_location)
        self.assertEqual(int_picking.package_level_ids.location_dest_id, self.shelfA_location)
        self.assertEqual(int_picking.move_lines.mapped('location_dest_id'), self.shelfA_location)
        self.assertEqual(int_picking.package_level_ids.move_ids.mapped('location_dest_id'), self.shelfA_location)
        self.assertEqual(int_picking.package_level_ids.move_line_ids.mapped('location_dest_id'), self.shelfA_location)

    def test_putaway_updates_package_level(self):
        self.two_steps_receive_rule.action = 'pull'
        in_picking, in_move_productA, in_move_productB = self._create_in_picking_with_moves()
        in_picking.action_confirm()
        in_move_productA.move_line_ids.qty_done = 10.0
        package_productA = in_picking.put_in_pack()
        in_move_productB.move_line_ids.qty_done = 10.0
        package_productB = in_picking.put_in_pack()
        in_picking.button_validate()

        int_picking = self.env['stock.picking'].create({
            'picking_type_id': self.internal_picking_type.id,
            'location_id': self.input_location.id,
            'location_dest_id': self.stock_location.id,
        })
        package_level_productA = self.env['stock.package_level'].create({
            'picking_id': int_picking.id,
            'package_id': package_productA.id,
            'location_id': self.input_location.id,
            'location_dest_id': self.stock_location.id,
        })
        package_level_productB = self.env['stock.package_level'].create({
            'picking_id': int_picking.id,
            'package_id': package_productB.id,
            'location_id': self.input_location.id,
            'location_dest_id': self.stock_location.id,
        })
        int_picking.action_confirm()
        int_picking.action_assign()
        self.assertEqual(package_level_productA.location_dest_id, self.shelfA_location)
        self.assertEqual(package_level_productA.move_ids.location_dest_id, self.shelfA_location)
        self.assertEqual(package_level_productA.move_line_ids.location_dest_id, self.shelfA_location)
        self.assertEqual(package_level_productB.location_dest_id, self.shelfB_location)
        self.assertEqual(package_level_productB.move_ids.location_dest_id, self.shelfB_location)
        self.assertEqual(package_level_productB.move_line_ids.location_dest_id, self.shelfB_location)

    def _create_in_picking_with_moves(self):
        in_picking = self.env['stock.picking'].create({
            'picking_type_id': self.receipt_picking_type.id,
            'location_id': self.vendors_location.id,
            'location_dest_id': self.input_location.id,
        })
        in_move_productA = self.env['stock.move'].create({
            'picking_id': in_picking.id,
            'name': 'TEST ProductA',
            'product_id': self.productA.id,
            'product_uom_qty': 10.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.vendors_location.id,
            'location_dest_id': self.input_location.id,
        })
        in_move_productB = self.env['stock.move'].create({
            'picking_id': in_picking.id,
            'name': 'TEST ProductB',
            'product_id': self.productB.id,
            'product_uom_qty': 10.0,
            'product_uom': self.productB.uom_id.id,
            'location_id': self.vendors_location.id,
            'location_dest_id': self.input_location.id,
        })
        return in_picking, in_move_productA, in_move_productB

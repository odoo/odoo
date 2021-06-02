# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestProcRule(TransactionCase):

    def setUp(self):
        super(TestProcRule, self).setUp()

        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.product = self.env['product.product'].create({
            'name': 'Desk Combination',
            'type': 'consu',
        })
        self.partner = self.env['res.partner'].create({'name': 'Partner'})

    def test_proc_rule(self):
        # Create a product route containing a stock rule that will
        # generate a move from Stock for every procurement created in Output
        product_route = self.env['stock.location.route'].create({
            'name': 'Stock -> output route',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Stock -> output rule',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': self.ref('stock.stock_location_stock'),
                'location_id': self.ref('stock.stock_location_output'),
            })],
        })

        # Set this route on `product.product_product_3`
        self.product.write({
            'route_ids': [(4, product_route.id)]})

        # Create Delivery Order of 10 `product.product_product_3` from Output -> Customer
        product = self.product
        vals = {
            'name': 'Delivery order for procurement',
            'partner_id': self.partner.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_lines': [(0, 0, {
                'name': '/',
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 10.00,
                'procure_method': 'make_to_order',
            })],
        }
        pick_output = self.env['stock.picking'].create(vals)
        pick_output.move_lines.onchange_product_id()

        # Confirm delivery order.
        pick_output.action_confirm()

        # I run the scheduler.
        # Note: If purchase if already installed, the method _run_buy will be called due
        # to the purchase demo data. As we update the stock module to run this test, the
        # method won't be an attribute of stock.procurement at this moment. For that reason
        # we mute the logger when running the scheduler.
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.env['procurement.group'].run_scheduler()

        # Check that a picking was created from stock to output.
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.ref('stock.stock_location_stock')),
            ('location_dest_id', '=', self.ref('stock.stock_location_output')),
            ('move_dest_ids', 'in', [pick_output.move_lines[0].id])
        ])
        self.assertEqual(len(moves.ids), 1, "It should have created a picking from Stock to Output with the original picking as destination")

    def test_rule_propagate_1(self):
        move_dest = self.env['stock.move'].create({
            'name': 'move_dest',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })

        move_orig = self.env['stock.move'].create({
            'name': 'move_orig',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'move_dest_ids': [(4, move_dest.id)],
            'propagate_date': True,
            'propagate_date_minimum_delta': 5,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
        })

        move_dest_initial_date = move_dest.date_expected

        # change above the minimum delta
        move_orig.date_expected += timedelta(days=6)
        self.assertAlmostEquals(move_dest.date_expected, move_dest_initial_date + timedelta(days=6), delta=timedelta(seconds=10), msg='date should be propagated as the minimum delta is below')

        # change below the minimum delta
        move_dest_initial_date = move_dest.date_expected
        move_orig.date_expected += timedelta(days=4)

        self.assertAlmostEquals(move_dest.date_expected, move_dest_initial_date, delta=timedelta(seconds=10), msg='date should not be propagated as the minimum delta is above')

    def test_rule_propagate_2(self):
        move_dest = self.env['stock.move'].create({
            'name': 'move_dest',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })

        move_orig = self.env['stock.move'].create({
            'name': 'move_orig',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'move_dest_ids': [(4, move_dest.id)],
            'propagate_date': False,
            'propagate_date_minimum_delta': 5,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
        })

        move_dest_initial_date = move_dest.date_expected

        # change below the minimum delta
        move_orig.date_expected += timedelta(days=4)
        self.assertAlmostEquals(move_dest.date_expected, move_dest_initial_date, delta=timedelta(seconds=10), msg='date should not be propagated')

        # change above the minimum delta
        move_orig.date_expected += timedelta(days=2)
        self.assertAlmostEquals(move_dest.date_expected, move_dest_initial_date, delta=timedelta(seconds=10), msg='date should not be propagated')

    def test_rule_propagate_3(self):
        move_dest = self.env['stock.move'].create({
            'name': 'move_dest',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })

        move_orig = self.env['stock.move'].create({
            'name': 'move_orig',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'move_dest_ids': [(4, move_dest.id)],
            'propagate_date': True,
            'propagate_date_minimum_delta': 5,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'quantity_done': 10,
        })
        move_orig.date_expected -= timedelta(days=6)
        move_dest_initial_date = move_dest.date_expected
        move_orig_initial_date = move_orig.date_expected
        move_orig._action_done()
        self.assertAlmostEquals(move_orig.date_expected, move_orig_initial_date, delta=timedelta(seconds=10), msg='schedule date should not be impacted by action_done')
        self.assertAlmostEquals(move_orig.date, datetime.now(), delta=timedelta(seconds=10), msg='date should be now')
        self.assertAlmostEquals(move_dest.date_expected, move_dest_initial_date + timedelta(days=6), delta=timedelta(seconds=10), msg='date should be propagated')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form
from odoo import fields



class TestStockReplenish(TestStockCommon):

    def test_base_delay(self):
        """Open the replenish view and check if delay is taken into account
            in the base date computation
        """
        stock_location = self.env.ref('stock.stock_location_stock')

        push_location = self.env['stock.location'].create({
            'location_id': stock_location.location_id.id,
            'name': 'push location',
        })

        route_no_delay = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': stock_location.id,
                'location_dest_id': push_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'delay': 0,
            })],
        })

        route_delay = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': stock_location.id,
                'location_dest_id': push_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'delay': 2,
            }),
            (0, False, {
                'name': 'create a move to push location',
                'location_src_id': push_location.id,
                'location_dest_id': stock_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'delay': 4,
            })],
        })

        with freeze_time("2023-01-01"):
            wizard = Form(self.env['product.replenish'])
            wizard.route_id = route_no_delay
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard._values['date_planned'])
            wizard.route_id = route_delay
            self.assertEqual(fields.Datetime.from_string('2023-01-07 00:00:00'), wizard._values['date_planned'])

    def test_replenish_no_routes(self):
        product = self.env['product.template'].create({
        'name': 'Brand new product',
        'type': 'product',
    })
        self.assertEqual(len(product.route_ids), 0)
        wizard = Form(self.env['product.replenish'].with_context(default_product_tmpl_id=product.id))
        self.assertEqual(wizard._values['quantity'], 1)

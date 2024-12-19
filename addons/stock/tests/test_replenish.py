# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form
from odoo import fields



class TestStockReplenish(TestStockCommon):
    def setUp(self):
        self.uid = self.user_stock_manager

    def test_base_delay(self):
        """Open the replenish view and check if delay is taken into account
            in the base date computation
        """
        push_location = self.env['stock.location'].create({
            'location_id': self.stock_location.location_id.id,
            'name': 'push location',
        })

        route_no_delay = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': self.stock_location.id,
                'location_dest_id': push_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.picking_type_in.id,
                'delay': 0,
            })],
        })

        route_delay = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'create a move to push location',
                'location_src_id': self.stock_location.id,
                'location_dest_id': push_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.picking_type_in.id,
                'delay': 2,
            }),
            (0, False, {
                'name': 'create a move to push location',
                'location_src_id': push_location.id,
                'location_dest_id': self.stock_location.id,
                'company_id': self.env.company.id,
                'action': 'push',
                'auto': 'manual',
                'picking_type_id': self.picking_type_in.id,
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
        'is_storable': True,
    })
        self.assertEqual(len(product.route_ids), 0)
        wizard = Form(self.env['product.replenish'].with_context(default_product_tmpl_id=product.id))
        self.assertEqual(wizard._values['quantity'], 1)

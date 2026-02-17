# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form
from odoo import Command, fields



class TestStockReplenish(TestStockCommon):

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
            'rule_ids': [Command.create({
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
            'rule_ids': [Command.create({
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

    def test_replenishment_wizard_multi_warehouse_routes(self):
        """ Ensure that in a multi-warehouse setup, the replenishment wizard only
            displays routes applicable to the selected warehouse."""
        def create_replenish_wizard(warehouse, product):
            return self.env['product.replenish'].create({
                'product_id': product.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_uom_id': product.uom_id.id,
                'warehouse_id': warehouse.id,
            })

        # Warehouse 1 should show reception route in replenishment wizard.
        replenish = create_replenish_wizard(self.warehouse_1, self.productA)
        self.assertEqual(replenish.allowed_route_ids, self.warehouse_1.reception_route_id)

        warehouse_2 = self.warehouse_1.copy({'name': 'Base Warehouse 2'})
        self.warehouse_1.write({
            'resupply_wh_ids': warehouse_2,
        })

        # Warehouse 1 should show both resupply and reception routes in replenishment wizard.
        replenish = create_replenish_wizard(self.warehouse_1, self.productA)
        self.assertRecordValues(replenish.allowed_route_ids, [
            {'id': self.warehouse_1.resupply_route_ids.id, 'name': 'Base Warehouse: Supply Product from Base Warehouse 2'},
            {'id': self.warehouse_1.reception_route_id.id, 'name': 'Base Warehouse: Receive in 1 step (stock)'},
        ])

        # Warehouse 2 should show only its reception route in replenishment wizard.
        replenish = create_replenish_wizard(warehouse_2, self.productA)
        self.assertRecordValues(replenish.allowed_route_ids, [
            {'id': warehouse_2.reception_route_id.id, 'name': 'Base Warehouse 2: Receive in 1 step (stock)'},
        ])

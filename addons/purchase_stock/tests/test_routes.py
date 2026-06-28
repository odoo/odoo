from odoo import Command
from odoo.tests import tagged, Form, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRoutes(TransactionCase):

    def test_allow_rule_creation_for_route_without_company(self):
        self.env['res.config.settings'].write({
            'group_stock_adv_location': True,
            'group_stock_multi_locations': True,
        })

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        location_1 = self.env['stock.location'].create({
            'name': 'loc1',
            'location_id': warehouse.lot_stock_id.id
        })

        location_2 = self.env['stock.location'].create({
            'name': 'loc2',
            'location_id': warehouse.lot_stock_id.id
        })

        receipt_1 = self.env['stock.picking.type'].create({
            'name': 'Receipts from loc1',
            'sequence_code': 'IN1',
            'code': 'incoming',
            'warehouse_id': warehouse.id,
            'default_location_dest_id': location_1.id,
        })

        receipt_2 = self.env['stock.picking.type'].create({
            'name': 'Receipts from loc2',
            'sequence_code': 'IN2',
            'code': 'incoming',
            'warehouse_id': warehouse.id,
            'default_location_dest_id': location_2.id,
        })

        route = self.env['stock.route'].create({
            'name': 'Buy',
            'company_id': False
        })

        with Form(route) as r:
            with r.rule_ids.new() as line:
                line.name = 'first rule'
                line.action = 'buy'
                line.picking_type_id = receipt_1
            with r.rule_ids.new() as line:
                line.name = 'second rule'
                line.action = 'buy'
                line.picking_type_id = receipt_2

    def test_delete_buy_route(self):
        """
        The user should be able to write on a warehouse even if the buy route
        does not exist anymore
        """
        wh = self.env['stock.warehouse'].search([], limit=1)

        buy_routes = self.env['stock.route'].search([('name', 'ilike', 'buy')])
        self.assertTrue(buy_routes)

        buy_routes.unlink()

        wh.reception_steps = 'two_steps'
        self.assertEqual(wh.reception_steps, 'two_steps')

    def test_buy_to_resupply_unchecks_and_unlinks_warehouse(self):
        """Unchecking Buy to Resupply should keep buy_to_resupply disabled."""
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        buy_route = wh.buy_pull_id.route_id
        wh.buy_to_resupply = False
        # Invalidate recordset to avoid cached `buy_to_resupply`
        wh.invalidate_recordset(["buy_to_resupply"])
        # Creating a new warehouse because if buy_route.warehouse_ids is empty and warehouse_selectable = True, it applies to all warehouses
        self.env['stock.warehouse'].create({'name': 'WH 2', 'code': 'WH2'})
        self.assertFalse(wh.buy_to_resupply)
        self.assertNotIn(wh, buy_route.warehouse_ids)

    def test_po_final_location(self):
        """
        When confirming PO with Operation Type is a sublocation, computation
        of the final location should take that into account so as to not
        interfere with forecasted quantity.
        """

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        sub_location = self.env['stock.location'].create({
            'name': 'test sub location',
            'location_id': warehouse.lot_stock_id.id,
        })

        warehouse.in_type_id.default_location_dest_id = sub_location

        product = self.env['product.product'].create({
            'name': 'test product',
            'is_storable': True,
        })

        partner = self.env['res.partner'].create({'name': 'test vendor'})

        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'picking_type_id': warehouse.in_type_id.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 10.0,
                'price_unit': 20.0,
            })],
        })
        po.button_confirm()

        move = po.picking_ids.move_ids
        self.assertEqual(move.location_dest_id, sub_location, "destination on move should be the sub-location")

        forecast = product.with_context(location=sub_location.id).virtual_available
        self.assertEqual(forecast, 10.0, "forecasted quantity should increment to 10.0 units")

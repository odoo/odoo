from odoo import Command
from odoo.tests import Form, TransactionCase


class TestRoutes(TransactionCase):

    def test_allow_rule_creation_for_route_without_company(self):
        self.env['res.config.settings'].write({
            'group_stock_adv_location': True,
            'group_stock_multi_locations': True,
        })

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        location_1 = self.env['stock.location'].create({
            'name': 'loc1',
            'location_id': warehouse.id
        })

        location_2 = self.env['stock.location'].create({
            'name': 'loc2',
            'location_id': warehouse.id
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
        self.assertEqual(move.location_final_id, sub_location, "location_final_id should be the sub-location")

        forecast = product.with_context(location=sub_location.id).virtual_available
        self.assertEqual(forecast, 10.0, "forecasted quantity should increment to 10.0 units")

    def test_product_create_with_inaccessible_buy_route(self):
        """
        Creating a product should not raise an AccessError when the buy route
        belongs to a company the user cannot access.
        """
        company_a = self.env.company
        company_b = self.env['res.company'].create({
            'name': 'Company B',
        })
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy')
        buy_route.rule_ids.unlink()
        buy_route.company_id = company_a

        # The user can only access Company B.
        user = self.env['res.users'].create({
            'name': 'Purchase User',
            'login': 'purchase_user_test',
            'company_id': company_b.id,
            'company_ids': [(6, 0, [company_b.id])],
            'groups_id': [(6, 0, [self.env.ref('purchase.group_purchase_manager').id])],
        })

        Product = (
            self.env['product.template']
            .with_user(user)
            .with_company(company_b)
        )

        self.assertFalse(
            Product._get_buy_route(),
            'A route from an inaccessible company must not be used by default',
        )
        with Form(Product) as product_form:
            product_form.name = 'Test Product'

        buy_route.company_id = company_b
        self.assertEqual(
            Product._get_buy_route(),
            buy_route.ids,
            'A route from the active company must still be used by default',
        )

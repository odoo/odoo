from odoo.tests.common import TransactionCase, Form


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

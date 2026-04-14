from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestStockWarehouseOrderpoint(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Book Shelf',
            'lst_price': 1750.00,
            'is_storable': True,
            'purchase_ok': True,
        })
        cls.res_partner_1 = cls.env['res.partner'].create({
            'name': 'Wood Corner',
        })
        cls.env['product.supplierinfo'].create([
            {
                'partner_id': cls.res_partner_1.id,
                'product_id': cls.product.id,
                'delay': 3,
                'min_qty': 1,
                'price': 750,
            }
        ])

    def test_product_replenishment(self):
        self.assertFalse(self.product.orderpoint_ids)

        self.start_tour("/odoo/replenishment", "test_product_replenishment", login='admin')

<<<<<<< b02a39d43e58118e92a794377e6a739015035d44
        self.assertEqual(len(self.product.orderpoint_ids), 1)
        self.assertEqual(self.product.orderpoint_ids[0].route_id.name, 'Buy')

    def test_default_buy_route_with_no_warehouse(self):
        route_domain = [
            ('warehouse_selectable', '=', True),
            ('rule_ids.action', '=', 'buy'),
            ('company_id', 'in', [False, self.env.company.id]),
        ]
        routes = self.env['stock.route'].search(route_domain)
        routes.warehouse_ids = False
        orderpoint = self.env['stock.warehouse.orderpoint'].create({'product_id': self.product.id})
        self.assertEqual(routes[0].name, orderpoint.route_id_placeholder)
||||||| 942cbbbf243ff28f84fdaa40ed73b6572e0032a6
        self.assertEqual(len(product.orderpoint_ids), 1)
        self.assertEqual(product.orderpoint_ids[0].route_id.name, 'Buy')
=======
        self.assertEqual(len(product.orderpoint_ids), 1)
        self.assertEqual(product.orderpoint_ids[0].route_id.name, 'Buy')

    def test_replenishment_supplier_multicompany_access(self):
        partner_a, partner_b = self.env['res.partner'].create([{'name': 'Partner A'}, {'name': 'Partner B'}])
        company_a, company_b = self.env.company, self.env['res.company'].create({'name': 'Company B'})
        product = self.env['product.product'].create({'name': 'Product A', 'is_storable': True})
        self.env['product.supplierinfo'].create([
            {'partner_id': partner.id, 'product_id': product.id, 'company_id': company.id, 'price': price}
            for company, price, partner in [(company_a, 10.0, partner_a), (company_b, 20.0, partner_b)]
        ])
        self.env.user.company_ids = company_a
        self.start_tour('/odoo/replenishment', 'test_replenishment_supplier_multicompany_access', login='admin')
>>>>>>> 189c14f6134ce32d6e7b54d16c7f5b7c7076923f

from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestStockWarehouseOrderpoint(HttpCase):

    def test_product_replenishment(self):
        product = self.env['product.product'].create({
            'name': 'Book Shelf',
            'lst_price': 1750.00,
            'is_storable': True,
            'purchase_ok': True,
        })
        self.assertFalse(product.orderpoint_ids)

        self.start_tour("/odoo/replenishment", "test_product_replenishment", login='admin')

        self.assertEqual(len(product.orderpoint_ids), 1)
        self.assertEqual(product.orderpoint_ids[0].route_id.name, 'Buy')

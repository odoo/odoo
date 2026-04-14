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

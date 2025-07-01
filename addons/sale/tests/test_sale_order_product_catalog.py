# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestSaleOrderProductCatalog(HttpCase):

    def test_sale_order_product_catalog_branch_company_tour(self):
        """Test adding products to a SO through the catalog view when in a branch company."""

        self.env['product.template'].create({
            'name': "Restricted Product",
            'company_id': self.env.company.id,
        })
        self.env['res.partner'].create({
            'name': "Test Partner",
        })
        admin = self.env.ref('base.user_admin')
        branch = self.env['res.company'].with_user(admin).create({
            'name': "Branch Company",
            'parent_id': self.env.company.id,
        })
        admin.company_id = branch
        self.env['product.template'].create({
            'name': "AAA Product",
            'company_id': admin.company_id.id,
        })
        self.start_tour(
            '/web#action=sale.action_quotations',
            'sale_catalog',
            login="admin",
        )

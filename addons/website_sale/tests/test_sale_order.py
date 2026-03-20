# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(WebsiteSaleCommon):

    def test_delivery_methods_match_order_company(self):
        company_1 = self.env['res.company'].create({'name': 'Test Company 1'})
        company_2 = self.env['res.company'].create({'name': 'Test Company 2'})
        product_delivery_1, product_delivery_2 = self.env['product.product'].create([
            {
                'name': 'Delivery Product 1',
                'type': 'service',
                'company_id': company_1.id,
            },
            {
                'name': 'Delivery Product 2',
                'type': 'service',
                'company_id': company_2.id,
            },
        ])
        delivery_1, delivery_2 = self.env['delivery.carrier'].create([
            {
                'name': 'Delivery 1',
                'delivery_type': 'fixed',
                'product_id': product_delivery_1.id,
                'is_published': True,
            },
            {
                'name': 'Delivery 2',
                'delivery_type': 'fixed',
                'product_id': product_delivery_2.id,
                'is_published': True,
            },
        ])
        sale_order = self.env['sale.order'].create(
            {
                'partner_id': self.partner.id,
                'company_id': company_1.id,
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product.id,
                        }
                    )],
            }
        )
        available_dms = sale_order._get_delivery_methods()
        self.assertIn(delivery_1, available_dms)
        self.assertNotIn(delivery_2, available_dms)

    def test_website_id_is_set_on_invoice(self):
        """Check that the website is correctly set on invoices created from e-commerce orders."""
        self.cart.action_confirm()
        invoice = self.cart._create_invoices()
        self.assertTrue(self.cart.website_id)
        self.assertEqual(
            self.cart.website_id,
            invoice.website_id,
        )

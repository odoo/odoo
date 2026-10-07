from odoo import Command
from odoo.tests import tagged, HttpCase

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestDashboard(WebsiteSaleCommon, HttpCase):

    def test_dashboard_refresh(self):
        self.env['sale.order'].create([
            {
                'partner_id': self.partner.id,
                'order_line': [
                    Command.create({'product_id': self.product.id}),
                    Command.create({'product_id': self.product.id})
                ],
                'website_id': self.website.id,
                'state': 'sent'
            } for _ in range(2)
        ])
        self.start_tour('/odoo/ecommerce-orders', 'test_dashboard_refresh', login='admin')

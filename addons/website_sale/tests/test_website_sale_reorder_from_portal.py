# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSaleReorderFromPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['website'].get_current_website().enabled_portal_reorder_button = True

    def test_website_sale_reorder_from_portal(self):
        product_1, product_2 = self.env['product.product'].create([
            {
                'name': 'Reorder Product 1',
                'sale_ok': True,
                'website_published': True,
            },
            {
                'name': 'Reorder Product 2',
                'sale_ok': True,
                'website_published': True,
            },
        ])
        user_admin = self.env.ref('base.user_admin')
        order = self.env['sale.order'].create({
            'partner_id': user_admin.partner_id.id,
            'state': 'sale',
            'order_line': [
                (0, 0, {
                    'product_id': product_1.id,
                }),
                (0, 0, {
                    'product_id': product_2.id,
                }),
            ],
        })
        order.message_subscribe(user_admin.partner_id.ids)

        self.start_tour("/", 'website_sale_reorder_from_portal', login='admin')

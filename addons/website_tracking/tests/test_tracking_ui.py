# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_recently_viewed_tour(self):

        products = [
            [7, 7],
            [22, 27],
            [9, 10]
        ]
        View = self.env['product.view']
        # Add 3 products for the tour.
        for product in products:
            View.create_productview({
                'res_partner_id': 3,
                'product_template_id': product[0],
                'last_product_id': product[1],
            })
        # Allow a user to sign in on website.
        current_website = self.env['website'].get_current_website()
        current_website.auth_signup_uninvited = 'b2c'

        self.start_tour("/", 'recently_viewed', login='admin')

        # Verify that the user cookie content has been registered in DB after sign in.
        user = self.env['res.users'].sudo().search([('login', '=', 'TestLogin')])
        product_views = View.search([('res_partner_id', '=', user.partner_id.id)], order='write_date')
        for product, product_view in zip(products, product_views):
            self.assertEqual(product_view.product_template_id.id, product[0])
            self.assertEqual(product_view.last_product_id.id, product[1])

        # Update a view already registered to make sure it's returned as most recent view.
        View.create_productview({
            'res_partner_id': 3,
            'product_template_id': 7,
            'last_product_id': 7,
        })
        product_view = View.search([('res_partner_id', '=', 3)], limit=1, order='write_date desc')
        self.assertEqual(product_view.product_template_id.id, 7)
        self.assertEqual(product_view.last_product_id.id, 7)

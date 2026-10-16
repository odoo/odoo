# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, Form
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo import Command


@tagged('post_install', '-at_install')
class TestControllersAccessRights(HttpCase, TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = mail_new_test_user(cls.env, login='jimmy-portal', groups='base.group_portal')

    def test_SO_and_DO_portal_acess(self):
        """ Ensure that it is possible to open both SO and DO, either using the access token
        or being connected as portal user"""
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.portal_user.partner_id
        with so_form.order_line.new() as line:
            line.product_id = self.product_a
        so = so_form.save()
        so.action_confirm()
        picking = so.picking_ids

        # Try to open SO/DO using the access token or being connected as portal user
        for login in (None, self.portal_user.login):
            so_url = '/my/orders/%s' % so.id
            picking_url = '/my/picking/pdf/%s' % picking.id

            self.authenticate(login, login)

            if not login:
                so._portal_ensure_token()
                so_token = so.access_token
                so_url = '%s?access_token=%s' % (so_url, so_token)
                picking_url = '%s?access_token=%s' % (picking_url, so_token)

            response = self.url_open(
                url=so_url,
                allow_redirects=False,
            )
            self.assertEqual(response.status_code, 200, 'Should be correct %s' % ('with a connected user' if login else 'using access token'))
            response = self.url_open(
                url=picking_url,
                allow_redirects=False,
            )
            self.assertEqual(response.status_code, 200, 'Should be correct %s' % ('with a connected user' if login else 'using access token'))

    def test_sale_stock_order_search_access(self):
        """
        Test that an inventory user with access only for its own sales documents
        can access sale documents linked to stock moves, even if they are linked to a sale order of another user.
        """
        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Inventory Test Customer'}).id,
            'order_line': [
                Command.create({'product_id': self.service_product.id}),   # Service product, no picking will be created
            ],
        })
        so.action_confirm()
        so_stock = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Inventory Test Customer'}).id,
            'order_line': [
                Command.create({'product_id': self.product.id}),
            ],
        })
        so_stock.action_confirm()

        user_own_sale = mail_new_test_user(
            self.env,
            login='test_sale_own_doc',
            groups='sales_team.group_sale_salesman',
        )
        visible_orders = self.env['sale.order'].with_user(user_own_sale).search([])
        self.assertNotIn(so_stock, visible_orders, "A sale user without inventory rights should not see that sale order as it's related to another user")

        user_own_sale.group_ids += self.env.ref('stock.group_stock_user')
        visible_orders = self.env['sale.order'].with_user(user_own_sale).search([])
        self.assertIn(so_stock, visible_orders, "The sale user should be able to access the sale order since it is linked to a stock moves he has access to")
        self.assertNotIn(so, visible_orders, "The sale user with inventory rights should however not see that sale order as it's related to another user and doesn't have any pickings linked to it")

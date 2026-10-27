# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, Form
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
class TestControllersAccessRights(HttpCase, TestSaleCommon):

    _test_user_groups = None  # FIXME list needed groups

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


@tagged('post_install', '-at_install')
class TestSaleOrderStockUserRules(TestSaleCommon):

    def test_stock_user_keeps_salesman_own_documents_restriction(self):
        """ A salesman restricted to own documents must not see every order
        just because he is also an inventory user. """
        env = self.env
        stock_user_group = 'stock.group_stock_user'
        salesman = mail_new_test_user(
            env, login='own-docs-stock', groups=f'sales_team.group_sale_salesman,{stock_user_group}')
        other_salesman = mail_new_test_user(
            env, login='other-salesman', groups='sales_team.group_sale_salesman')
        warehouse_only = mail_new_test_user(
            env, login='warehouse-only', groups=stock_user_group)

        other_order, own_order, free_order = env['sale.order'].create([
            {'partner_id': self.partner_a.id, 'user_id': other_salesman.id},
            {'partner_id': self.partner_a.id, 'user_id': salesman.id},
            {'partner_id': self.partner_a.id, 'user_id': False},
        ])
        for order in (other_order, own_order, free_order):
            env['sale.order.line'].create({
                'order_id': order.id, 'product_id': self.product_a.id})
        orders = other_order | own_order | free_order

        visible = orders.with_user(salesman).search([('id', 'in', orders.ids)])
        self.assertEqual(visible, own_order | free_order)
        visible_lines = env['sale.order.line'].with_user(salesman).search(
            [('order_id', 'in', orders.ids)])
        self.assertEqual(visible_lines.order_id, own_order | free_order)

        # a pure inventory user still sees every order (needed for deliveries)
        visible = orders.with_user(warehouse_only).search([('id', 'in', orders.ids)])
        self.assertEqual(visible, orders)

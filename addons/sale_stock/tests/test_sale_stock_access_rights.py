# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, Form
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.mail.tests.common import mail_new_test_user


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

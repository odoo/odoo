# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo

from odoo import SUPERUSER_ID, fields
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install', 'mail_thread')
class TestWebsiteSaleMail(HttpCaseWithUserPortal):

    def test_01_shop_mail_tour(self):
        """The goal of this test is to make sure sending SO by email works."""
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        self.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'list_price': 2950.0,
            'sale_ok': True,
            'website_published': True,
        })
        self.env['res.partner'].create({
            'name': 'Azure Interior',
            'email': 'azure.Interior24@example.com',
        })

        # we override unlink because we don't want the email to be auto deleted
        MailMail = odoo.addons.mail.models.mail_mail.MailMail
        # as we check some link content, avoid mobile doing its link management
        self.env['ir.config_parameter'].sudo().set_param('mail_mobile.disable_redirect_firebase_dynamic_link', True)

        main_website = self.env.ref('website.default_website')
        other_websites = self.env['website'].search([]) - main_website

        # We change the domain of the website to test that the email that
        # will be sent uses the correct domain for its links.
        main_website.domain = "my-test-domain.com"
        for w in other_websites:
            w.domain = f'domain-not-used-{w.id}.fr'
        with patch.object(MailMail, 'unlink', lambda self: None):
            start_time = fields.Datetime.now()
            self.start_tour("/", 'shop_mail', login="admin")
            new_mail = self.env['mail.mail'].search([('create_date', '>=', start_time),
                                                     ('body_html', 'ilike', 'https://my-test-domain.com')],
                                                    order='create_date DESC', limit=None)
            self.assertTrue(new_mail)
            self.assertIn('Your', new_mail.body_html)
            self.assertIn('order', new_mail.body_html)

    def test_shop_product_mail_action_redirection(self):
        product_template = self.env['product.template'].create({
            'name': "test product template",
            'sale_ok': True,
            'website_published': True,
        })
        url = f'/mail/view?model=product.template&res_id={product_template.id}'
        shop_url = f'/shop/test-product-template-{product_template.id}'

        with self.subTest(user='admin'):
            self.authenticate('admin', 'admin')
            res = self.url_open(url)
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.request.path_url.startswith('/odoo/product.template'))

        with self.subTest(user='portal'):
            self.authenticate('portal', 'portal')
            res = self.url_open(url)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.request.path_url, shop_url)

        with self.subTest(user=None):
            self.authenticate(None, None)
            res = self.url_open(url)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.request.path_url, shop_url)


@tagged('post_install', '-at_install', 'mail_thread')
class TestWebsiteSaleMails(MailCommon, WebsiteSaleCommon):

    def test_salesman_assignation(self):
        self.website.salesperson_id = self.user_admin
        MailThread = odoo.addons.mail.models.mail_thread.MailThread
        base_method = MailThread._message_create
        superuser = self.env['res.users'].browse(SUPERUSER_ID)

        # Public user
        with patch.object(
            MailThread, '_message_create', autospec=True, side_effect=base_method
        ) as patcher:
            self.cart.with_user(self.public_user).with_context(tracking_disable=False, mail_no_track=False).sudo().action_confirm()
            patcher.assert_called()

            order, msg_values = None, {}
            for (record, call_args), _whatever in patcher.call_args_list:
                if record._name == 'sale.order':
                    order = record
                    msg_values = call_args[0]
                    break

            self.assertEqual(order, self.cart)
            self.assertEqual(msg_values['author_id'], superuser.partner_id.id)
            self.assertEqual(msg_values['partner_ids'], self.partner_admin.ids)
            self.assertEqual(msg_values['subject'], f"You have been assigned to {order.name}")

        # Portal user
        user_portal = self._create_portal_user()
        portal_partner = user_portal.partner_id
        portal_user_cart = self.cart.copy({'partner_id': portal_partner.id, 'user_id': False})
        with patch.object(
            MailThread, '_message_create', autospec=True, side_effect=base_method
        ) as patcher:
            portal_user_cart.with_user(user_portal).with_context(tracking_disable=False, mail_no_track=False).sudo().action_confirm()
            patcher.assert_called()

            order, msg_values = None, {}
            for (record, call_args), _whatever in patcher.call_args_list:
                if record._name == 'sale.order':
                    order = record
                    msg_values = call_args[0]
                    break

            self.assertEqual(order, portal_user_cart)
            self.assertEqual(msg_values['author_id'], superuser.partner_id.id)
            self.assertEqual(msg_values['partner_ids'], self.partner_admin.ids)
            self.assertEqual(msg_values['subject'], f"You have been assigned to {order.name}")

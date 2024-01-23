# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleMail(HttpCase):

    def test_01_shop_mail_tour(self):
        """The goal of this test is to make sure sending SO by email works."""
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
                                                    order='create_date DESC', limit=1)
            self.assertTrue(new_mail)
            self.assertIn('Your', new_mail.body_html)
            self.assertIn('Order', new_mail.body_html)

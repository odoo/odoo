# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.models import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteRedirect(TransactionCase):
    def test_01_website_redirect_validation(self):
        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/',
            })
        self.assertIn('homepage', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico',
            })
        self.assertIn('existing page', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico/',  # trailing slash on purpose
            })
        self.assertIn('existing page', str(error.exception))

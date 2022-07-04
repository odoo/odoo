# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', 'at_install')
class TestWebLogin(HttpCase):
    def test_login(self):
        response = self.url_open('/web/login')
        self.assertEqual(response.status_code, 200)

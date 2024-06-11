# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase


class TestWebController(HttpCase):
    def test_health(self):
        response = self.url_open('/web/health')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'pass')
        self.assertFalse(response.cookies.get('session_id'))

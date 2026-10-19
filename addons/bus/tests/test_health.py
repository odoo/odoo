# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestBusController(HttpCase):
    def test_health(self):
        response = self.url_open('/websocket/health')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'pass')
        self.assertFalse(response.cookies.get('session_id'))

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestScopedApp(HttpCase):

    def test_scoped_app_is_a_frontend_route(self):
        response = self.url_open('/scoped_app?app_id=test&path=/test&app_name=Test')
        self.assertEqual(response.status_code, 200)

        match = re.search(r'odoo\.__session_info__\s*=\s*(\{.*?\});', response.text, re.S)
        self.assertTrue(match, "the scoped app page must expose a session")
        session_info = json.loads(match.group(1))

        self.assertTrue(session_info['is_frontend'])
        self.assertIn('lang_url_code', session_info)

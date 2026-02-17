# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2
from unittest.mock import patch

from odoo.tests import tagged, HttpCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebController(HttpCase):
    def test_health(self):
        response = self.url_open('/web/health')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'pass')
        self.assertFalse(response.cookies.get('session_id'))

    def test_health_db_server_status(self):
        response = self.url_open('/web/health?db_server_status=1')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'pass')
        self.assertEqual(payload['db_server_status'], True)
        self.assertFalse(response.cookies.get('session_id'))

        def _raise_psycopg2_error(*args):
            raise psycopg2.Error('boom')

        with patch('odoo.sql_db.db_connect', new=_raise_psycopg2_error):
            response = self.url_open('/web/health?db_server_status=1')
            self.assertEqual(response.status_code, 500)
            payload = response.json()
            self.assertEqual(payload['status'], 'fail')
            self.assertEqual(payload['db_server_status'], False)


@tagged('-at_install', 'post_install')
class TestCloc(HttpCase):
    def test_cloc_user_space(self):
        action = self.env["ir.actions.server"].create({
            "name": "test cloc user space",
            "model_id": self.env["ir.model"]._get("res.partner").id,
            "state": "code",
            "code": "action = {}"
        })
        self.start_tour("/odoo?debug=1", "test_cloc_user_space", login="admin")

        result = self.make_jsonrpc_request("/web/cloc")
        self.assertDictEqual(result, {
            'records': [{
                'all_lines': 1,
                'billable': True,
                'code_lines': 1,
                'display_name': 'test cloc user space',
                'id': action.id,
                'model': 'ir.actions.server',
                'module': 'odoo/studio'}],
            'total_billable': 1,
            'total_lines': 1
        })

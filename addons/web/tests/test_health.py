from unittest.mock import patch

import psycopg

from odoo.tests import HttpCase, tagged


@tagged("web_http", "web_health")
class TestWebController(HttpCase):
    def test_health(self):
        response = self.url_open("/web/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pass")
        self.assertFalse(response.cookies.get("session_id"))

    def test_health_db_server_status(self):
        response = self.url_open("/web/health?db_server_status=1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["db_server_status"], True)
        self.assertFalse(response.cookies.get("session_id"))

        def _raise_psycopg_error(*args):
            raise psycopg.Error("boom")

        with patch("odoo.db.db_connect", new=_raise_psycopg_error):
            response = self.url_open("/web/health?db_server_status=1")
            self.assertEqual(response.status_code, 500)
            payload = response.json()
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["db_server_status"], False)

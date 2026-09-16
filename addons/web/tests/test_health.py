import os
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

    def test_healthz_liveness(self):
        response = self.url_open("/web/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "pass"})
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertFalse(response.cookies.get("session_id"))

    def test_readyz_pass(self):
        response = self.url_open("/web/readyz")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checks"]["db"], "pass")
        self.assertEqual(payload["checks"]["data_dir"], "pass")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_readyz_db_fail(self):
        def _raise_psycopg_error(*args):
            raise psycopg.Error("boom")

        with patch("odoo.db.db_connect", new=_raise_psycopg_error):
            response = self.url_open("/web/readyz")
            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["checks"]["db"], "fail")

    def test_readyz_registries_pass_once_the_preload_is_done(self):
        response = self.url_open("/web/readyz")
        self.assertEqual(response.json()["checks"]["registries"], "pass")

    def test_readyz_loading_while_a_registry_preloads(self):
        with patch("odoo.service.server.is_ready", return_value=False):
            response = self.url_open("/web/readyz")
            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["checks"]["registries"], "loading")

    def test_readyz_data_dir_fail(self):
        with patch(
            "odoo.addons.web.controllers.health.os.access",
            return_value=False,
        ):
            response = self.url_open("/web/readyz")
            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["checks"]["data_dir"], "fail")


@tagged("web_http", "web_metrics")
class TestWebMetrics(HttpCase):
    def test_absent_without_a_token(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ODOO_METRICS_TOKEN", None)
            response = self.url_open("/web/metrics")
        self.assertEqual(response.status_code, 404)

    def test_absent_even_when_a_token_is_offered(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ODOO_METRICS_TOKEN", None)
            response = self.url_open(
                "/web/metrics", headers={"Authorization": "Bearer anything"}
            )
        self.assertEqual(response.status_code, 404)

    def test_rejects_a_missing_or_wrong_token(self):
        logger = "odoo.addons.web.controllers.health"
        with (
            patch.dict(os.environ, {"ODOO_METRICS_TOKEN": "right"}),
            self.assertLogs(logger, "WARNING") as capture,
        ):
            self.assertEqual(self.url_open("/web/metrics").status_code, 401)
            self.assertEqual(
                self.url_open(
                    "/web/metrics", headers={"Authorization": "Bearer wrong"}
                ).status_code,
                401,
            )
            self.assertEqual(
                self.url_open(
                    "/web/metrics", headers={"Authorization": "Basic right"}
                ).status_code,
                401,
            )
        self.assertEqual(len(capture.output), 3)

    def test_serves_the_exposition_with_a_valid_token(self):
        with patch.dict(os.environ, {"ODOO_METRICS_TOKEN": "right"}):
            response = self.url_open(
                "/web/metrics", headers={"Authorization": "Bearer right"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["Content-Type"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        body = response.text
        self.assertIn("odoo_up 1", body)
        self.assertIn("# TYPE odoo_pool_borrows_total counter", body)

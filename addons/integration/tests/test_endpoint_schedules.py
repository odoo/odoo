from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "integration")
class TestHealthCheckInterval(TransactionCase):
    def _service(self, code, minutes_ago, interval=60):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://api.schedule.test",
                "health_check_enabled": True,
                "health_check_interval": interval,
                "last_health_check": minutes_ago is not None
                and fields.Datetime.now() - timedelta(minutes=minutes_ago),
            }
        )

    def test_the_cron_only_checks_endpoints_whose_interval_has_passed(self):
        Endpoint = self.env["integration.service"]
        Endpoint.search([]).write({"health_check_enabled": False})
        recent = self._service("probe_recent", minutes_ago=10)
        due = self._service("probe_due", minutes_ago=90)
        never = self._service("probe_never", minutes_ago=None)
        checked = []

        with patch.object(
            type(Endpoint),
            "_probe_health",
            lambda self: checked.append(self.code),
        ):
            Endpoint.cron_health_check_all()

        self.assertEqual(sorted(checked), sorted([due.code, never.code]))
        self.assertNotIn(recent.code, checked)


@tagged("post_install", "-at_install", "integration")
class TestPerEndpointLogRetention(TransactionCase):
    def _endpoint(self, code, retention):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://api.retention.test",
                "log_retention_days": retention,
            }
        )

    def _old_log(self, endpoint, days):
        log = self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": f"integration.service,{endpoint.id}",
                "request_method": "GET",
                "request_url": "https://api.retention.test/x",
                "state": "success",
            }
        )
        self.env.cr.execute(
            "UPDATE integration_exchange SET date_completed = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=days), log.id),
        )
        return log

    def test_an_endpoint_retention_overrides_the_global_one(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.log_retention_days", "90"
        )
        short = self._endpoint("probe_short", retention=7)
        default = self._endpoint("probe_default", retention=0)
        short_log = self._old_log(short, days=10)
        default_log = self._old_log(default, days=10)

        self.env["integration.exchange"]._gc_old_logs()

        self.assertFalse(short_log.exists())
        self.assertTrue(default_log.exists())

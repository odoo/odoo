import contextlib
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import RateLimitError


@tagged("post_install", "-at_install", "integration")
class TestRateLimiter(APITransportTestCase):
    def _drain_bucket(self, service):
        bucket = (
            self.env["rate.limit.bucket"]
            .sudo()
            .get_or_create_bucket(service, self.env.company.id)
        )
        bucket.write({"tokens": 0.0, "last_refill": fields.Datetime.now()})
        return bucket

    @patch("requests.Session.request")
    def test_rate_limit_not_exceeded(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_rate_limit")

        for i in range(5):
            response = client.get(f"/test/{i}")
            self.assertEqual(response["status_code"], 200)

        self.flush_pending_logs()
        logs = self.env["integration.exchange"].search(
            [
                (
                    "channel_id",
                    "=",
                    f"integration.service,{self.service_with_rate_limit.id}",
                )
            ]
        )
        self.assertEqual(len(logs), 5)

    @patch("requests.Session.request")
    def test_rate_limit_exceeded(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_rate_limit")

        self._drain_bucket(self.service_with_rate_limit)

        with self.assertRaises(RateLimitError) as context:
            client.get("/test/new")

        self.assertIn("Rate limit exceeded", str(context.exception))

    @patch("requests.Session.request")
    def test_rate_limit_different_periods(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        service_per_second = self.env["integration.service"].create(
            {
                "name": "Per Second Rate Limit",
                "code": "test_rate_per_second",
                "category": "other",
                "endpoint_url": "https://api.persecond.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "rate_limit_enabled": True,
                "rate_limit_requests": 5,
                "rate_limit_period": "second",
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "Per Second Credential",
                "endpoint_id": service_per_second.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        client = get_api_client(self.env, "test_rate_per_second")

        with freeze_time(fields.Datetime.now()):
            self._drain_bucket(service_per_second)

            with self.assertRaises(RateLimitError):
                client.get("/test")

    @patch("requests.Session.request")
    def test_rate_limit_window_sliding(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_rate_limit")

        old_time = fields.Datetime.now() - timedelta(minutes=2)
        for _i in range(10):
            self.create_request_log(
                service=self.service_with_rate_limit,
                timestamp=old_time,
            )

        response = client.get("/test/new")
        self.assertEqual(response["status_code"], 200)

    def test_rate_limit_disabled(self):
        service_no_limit = self.env["integration.service"].create(
            {
                "name": "No Rate Limit",
                "code": "test_no_rate_limit",
                "category": "other",
                "endpoint_url": "https://api.nolimit.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "rate_limit_enabled": False,
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "No Limit Credential",
                "endpoint_id": service_no_limit.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        self.assertFalse(service_no_limit.rate_limit_enabled)

    @patch("requests.Session.request")
    def test_rate_limit_hour_period(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        service_per_hour = self.env["integration.service"].create(
            {
                "name": "Per Hour Rate Limit",
                "code": "test_rate_per_hour",
                "category": "other",
                "endpoint_url": "https://api.perhour.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "rate_limit_enabled": True,
                "rate_limit_requests": 100,
                "rate_limit_period": "hour",
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "Per Hour Credential",
                "endpoint_id": service_per_hour.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        client = get_api_client(self.env, "test_rate_per_hour")

        self._drain_bucket(service_per_hour)

        with self.assertRaises(RateLimitError):
            client.get("/test")

    @patch("requests.Session.request")
    def test_rate_limit_day_period(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        service_per_day = self.env["integration.service"].create(
            {
                "name": "Per Day Rate Limit",
                "code": "test_rate_per_day",
                "category": "other",
                "endpoint_url": "https://api.perday.com",
                "environment": "production",
                "company_id": self.env.company.id,
                "rate_limit_enabled": True,
                "rate_limit_requests": 1000,
                "rate_limit_period": "day",
            }
        )

        self.env["credential.credential"].create(
            {
                "name": "Per Day Credential",
                "endpoint_id": service_per_day.id,
                "company_id": self.env.company.id,
                "category_id": self.cat_custom.id,
                "environment": "production",
                "credential_value": "test_token",
            }
        )

        client = get_api_client(self.env, "test_rate_per_day")

        self._drain_bucket(service_per_day)

        with self.assertRaises(RateLimitError):
            client.get("/test")

    @patch("requests.Session.request")
    def test_rate_limit_logging(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_rate_limit")

        self._drain_bucket(self.service_with_rate_limit)

        with contextlib.suppress(RateLimitError):
            client.get("/test")

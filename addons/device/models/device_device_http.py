import json
import logging
import random

import requests

from odoo import fields, models

from odoo.addons.integration.tools import CommError

_logger = logging.getLogger(__name__)


class DeviceDeviceHttp(models.Model):
    _inherit = "device.device"

    def _protocol_display_endpoint(self):
        self.check_singleton()
        if self.comm_protocol in ("http", "https"):
            host = self._get_effective_endpoint()
            if not host:
                return False
            endpoint = f"{self.comm_protocol}://{host}"
            port = self._get_port_effective()
            if port:
                endpoint += f":{port}"
            if self.http_endpoint_path:
                endpoint += self.http_endpoint_path
            return endpoint
        return super()._protocol_display_endpoint()

    def http_connect(self):
        return self.http_read_data() is not None

    def https_connect(self):
        return self.http_connect()

    def http_disconnect(self):
        self._write_state_retry(
            {"connection_state": "disconnected"},
            "device: http disconnect",
        )
        return True

    def http_read_data(self):
        connection = self._require_connection()
        url = connection._base_url()
        if not url:
            raise ValueError(f"No endpoint configured for device {self.name}")
        if self.http_endpoint_path:
            path = self.http_endpoint_path
            if not path.startswith("/"):
                path = "/" + path
            url = url.rstrip("/") + path

        headers = {}
        effective_http_headers = self._get_effective_http_headers()
        if effective_http_headers:
            try:
                headers = json.loads(effective_http_headers)
            except json.JSONDecodeError:
                _logger.warning("Invalid JSON in HTTP headers for device %s", self.name)

        _logger.info("HTTP request to %s for device %s", url, self.name)
        http_method = self.config_id.http_method or "GET"
        # The connection carries the secret (basic, digest, bearer, API key),
        # the service the timeouts, the breaker and the budget.
        try:
            response = connection._get_api_client().request(
                http_method, url, headers=headers, raw=True
            )
        except CommError as e:
            raise requests.RequestException(str(e)) from e

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
        else:
            data = {"raw": response.text}

        self._write_state_retry(
            {
                "connection_state": "connected",
                "connection_state_message": f"HTTP {response.status_code}",
            },
            "device: http read connected",
        )

        raw_payload_str = json.dumps(data) if isinstance(data, dict) else str(data)
        self._store_data_point(
            data,
            source_topic=url,
            raw_payload=raw_payload_str,
            source="iot",
        )
        return data

    def https_disconnect(self):
        return self.http_disconnect()

    def https_read_data(self):
        return self.http_read_data()

    def _get_effective_http_headers(self):
        self.check_singleton()
        if self.http_headers:
            return self.http_headers
        return self.config_id.http_headers if self.config_id else ""

    def _demo_generate_http_data(self):
        self.check_singleton()

        demo_data = {
            "demo": True,
            "timestamp": fields.Datetime.now().isoformat(),
            "temperature": round(20 + random.uniform(-5, 5), 2),
            "humidity": round(50 + random.uniform(-20, 20), 2),
            "status": random.choice(["online", "active", "operational"]),
        }

        _logger.info("Generating HTTP demo data for device %s", self.name)

        self._write_state_retry(
            {
                "connection_state": "connected",
                "connection_state_message": "Demo device (mock data)",
            },
            "device: demo http connected",
        )

        self._store_data_point(
            demo_data,
            source_topic=f"{self.comm_protocol}://{self.endpoint}:{self.port or 80}",
            raw_payload=json.dumps(demo_data),
        )

        return demo_data

    def _demo_generate_https_data(self):
        return self._demo_generate_http_data()

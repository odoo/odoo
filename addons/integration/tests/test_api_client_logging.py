import json
import re
import traceback
from unittest.mock import MagicMock, patch

import requests
from requests.auth import HTTPDigestAuth

from odoo.exceptions import UserError, ValidationError
from odoo.libs import redact
from odoo.libs.logging import mute_logger
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.integration.tools.api_client import _MAX_LOGGED_PAYLOAD
from odoo.addons.integration.tools.exceptions import ClientError, CommError

SECRET_KEY = "-----BEGIN PRIVATE KEY-----MIIEvQIBADANBg"

SECRET_VALUE = "redaction-probe-must-never-appear"

SW_ALREADY_STAMPED = {
    "status": "error",
    "message": "307 - El comprobante contiene un timbre previo",
    "messageDetail": "<cfdi:Comprobante>…already signed…</cfdi:Comprobante>",
    "data": None,
}


def _ok_response():
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {"status": "success"}
    response.text = '{"status": "success"}'
    response.raise_for_status.return_value = None
    return response


def _error_response(status_code, json_data):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.json.return_value = json_data
    response.text = json.dumps(json_data)
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{status_code} Client Error", response=response
    )
    return response


class ClientLoggingCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Payload Probe",
                "code": "payload_probe",
                "endpoint_url": "https://example.invalid/live",
                "auth_type": "none",
                "environment": "production",
            }
        )

    def _client(self):
        return self.service._get_api_client()


@tagged("post_install", "-at_install")
class TestPayloadSerialization(ClientLoggingCommon):
    def test_dict_body_is_redacted_key_by_key(self):
        out = self._client()._serialize_payload_for_log(
            {"rfc": "XAXX010101000", "password": SECRET_VALUE},
        )
        self.assertIn("XAXX010101000", out)
        self.assertNotIn(SECRET_VALUE, out)
        self.assertIn("***REDACTED***", out)

    def test_json_bytes_body_is_parsed_and_redacted(self):
        out = self._client()._serialize_payload_for_log(
            json.dumps({"uuid": "abc-123", "password": SECRET_VALUE}).encode(),
        )
        self.assertIn("abc-123", out)
        self.assertNotIn(SECRET_VALUE, out)

    def test_json_str_body_is_parsed_and_redacted(self):
        out = self._client()._serialize_payload_for_log(
            json.dumps({"uuid": "abc-123", "password": SECRET_VALUE}),
        )
        self.assertIn("abc-123", out)
        self.assertNotIn(SECRET_VALUE, out)

    def test_key_material_under_an_unmatched_name_is_still_not_stored(self):
        out = self._client()._serialize_payload_for_log(
            f"rfc=XAXX010101000&b64Key={SECRET_KEY}".encode(),
        )
        self.assertNotIn(SECRET_KEY, out)
        self.assertIn("not logged", out)

    def test_binary_body_is_recorded_by_size_only(self):
        out = self._client()._serialize_payload_for_log(
            b"\x49\x44\x33" + bytes(range(256))
        )
        self.assertIn("259 bytes", out)
        self.assertIn("not logged", out)

    def test_unparseable_text_body_is_recorded_by_size_only(self):
        out = self._client()._serialize_payload_for_log("<xml>not json</xml>")
        self.assertIn("19 chars", out)
        self.assertIn("not logged", out)

    def test_json_scalar_is_not_mistaken_for_structure(self):
        out = self._client()._serialize_payload_for_log('"just a string"')
        self.assertIn("not logged", out)

    def test_uninspectable_body_is_not_consumed(self):
        body = (chunk for chunk in (b"a", b"b"))
        out = self._client()._serialize_payload_for_log(body)
        self.assertIn("generator", out)
        self.assertEqual(list(body), [b"a", b"b"])

    def test_empty_body_is_empty_string(self):
        self.assertEqual(self._client()._serialize_payload_for_log(None), "")
        self.assertEqual(self._client()._serialize_payload_for_log(b""), "")

    def test_large_body_is_capped(self):
        out = self._client()._serialize_payload_for_log({"k": "v" * 40000})
        self.assertEqual(len(out), _MAX_LOGGED_PAYLOAD)


@tagged("post_install", "-at_install")
class TestUsageTrackingOnAnUnauthenticatedService(ClientLoggingCommon):
    def test_the_service_under_test_really_has_no_credential(self):
        self.assertFalse(self._client().credential)

    @patch("requests.Session.request")
    def test_a_successful_call_returns_its_response(self, mock_request):
        mock_request.return_value = _ok_response()

        result = self._client().post("/report", json={"rows": []})

        self.assertEqual(result["status_code"], 200)

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_failing_call_still_raises_the_transport_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError("down")

        with self.assertRaises(CommError):
            self._client().post("/report", json={"rows": []})


@tagged("post_install", "-at_install")
class TestLoggingCannotFailTheRequest(ClientLoggingCommon):
    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    @mute_logger("odoo.addons.integration.tools.api_client")
    def test_a_broken_serializer_does_not_raise(self):
        client = self._client()
        with patch.object(
            type(client),
            "_serialize_payload_for_log",
            side_effect=RuntimeError("boom"),
        ):
            client._log_request("POST", "https://example.invalid/x", {}, None, "t-1")
        self.assertEqual(self._queued(), [], "nothing should have been queued")

    @patch("requests.Session.request")
    def test_a_binary_body_neither_crashes_nor_fails_the_credential(self, mock_request):
        mock_request.return_value = _ok_response()

        client = self._client()
        result = client.post("/listen", data=b"\x00\x01\x02audio")

        self.assertEqual(result["body"], {"status": "success"})
        rows = self._queued()
        self.assertEqual(len(rows), 1, "the exchange should be recorded")
        self.assertNotEqual(rows[0]["state"], "failed")
        self.assertIn("not logged", rows[0]["request_payload"])

    @patch("requests.Session.request")
    def test_a_serialized_json_body_is_redacted_in_the_row(self, mock_request):
        mock_request.return_value = _ok_response()

        client = self._client()
        client.post(
            "/cancel",
            data=json.dumps({"uuid": "abc-123", "password": SECRET_VALUE}).encode(),
        )

        rows = self._queued()
        self.assertEqual(len(rows), 1)
        self.assertIn("abc-123", rows[0]["request_payload"])
        self.assertNotIn(SECRET_VALUE, rows[0]["request_payload"])


@tagged("post_install", "-at_install")
class TestRaiseForStatus(ClientLoggingCommon):
    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_4xx_still_raises_by_default(self, mock_request):
        mock_request.return_value = _error_response(400, SW_ALREADY_STAMPED)

        with self.assertRaises(ClientError):
            self._client().post("/stamp", json={})

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_4xx_is_returned_when_asked(self, mock_request):
        mock_request.return_value = _error_response(400, SW_ALREADY_STAMPED)

        result = self._client().post("/stamp", json={}, raise_for_status=False)

        self.assertEqual(result["status_code"], 400)
        self.assertEqual(result["body"]["status"], "error")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_the_recoverable_detail_survives(self, mock_request):
        mock_request.return_value = _error_response(400, SW_ALREADY_STAMPED)

        result = self._client().post("/stamp", json={}, raise_for_status=False)

        self.assertIn("already signed", result["body"]["messageDetail"])

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_not_raising_is_still_a_failure_in_the_audit_trail(self, mock_request):
        mock_request.return_value = _error_response(400, SW_ALREADY_STAMPED)

        self._client().post("/stamp", json={}, raise_for_status=False)

        rows = self._queued()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], "failed")
        self.assertEqual(rows[0]["error_type"], "validation")
        self.assertEqual(rows[0]["status_code"], 400)

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_status_maps_onto_the_declared_error_types(self, mock_request):
        for status, expected in ((401, "auth"), (429, "rate_limit"), (503, "server")):
            with self.subTest(status=status):
                self.env.cr.precommit.data.pop("integration.exchange.values", None)
                mock_request.return_value = _error_response(status, {"m": "no"})

                self._client().get("/probe", raise_for_status=False)

                self.assertEqual(self._queued()[-1]["error_type"], expected)

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_2xx_is_unaffected_by_the_flag(self, mock_request):
        mock_request.return_value = _ok_response()

        result = self._client().post("/stamp", json={}, raise_for_status=False)

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(self._queued()[0]["state"], "success")


@tagged("post_install", "-at_install")
class TestSuppressedRequestPayload(ClientLoggingCommon):
    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    def test_the_flag_defaults_to_storing_bodies(self):
        self.assertTrue(self.service.log_request_payload)

    @patch("requests.Session.request")
    def test_the_body_is_not_stored_when_suppressed(self, mock_request):
        mock_request.return_value = _ok_response()
        self.service.log_request_payload = False

        self._client().post("/cancel", json={"b64Key": SECRET_KEY, "uuid": "abc-123"})

        payload = self._queued()[0]["request_payload"]
        self.assertNotIn(SECRET_KEY, payload)
        self.assertIn("suppressed", payload)

    @patch("requests.Session.request")
    def test_the_rest_of_the_exchange_is_still_recorded(self, mock_request):
        mock_request.return_value = _ok_response()
        self.service.log_request_payload = False

        self._client().post("/cancel", json={"b64Key": SECRET_KEY})

        row = self._queued()[0]
        self.assertEqual(row["status_code"], 200)
        self.assertEqual(row["request_method"], "POST")
        self.assertIn("/cancel", row["request_url"])
        self.assertTrue(row["trace_id"])

    @patch("requests.Session.request")
    def test_known_gap_the_name_based_redactor_does_not_catch_b64key(
        self, mock_request
    ):
        mock_request.return_value = _ok_response()

        self._client().post("/cancel", json={"b64Key": SECRET_KEY})

        self.assertIn(SECRET_KEY, self._queued()[0]["request_payload"])


@tagged("post_install", "-at_install")
class TestRawPassthroughLogging(ClientLoggingCommon):
    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    @patch("requests.Session.request")
    def test_a_raw_call_records_status_and_timing(self, mock_request):
        mock_request.return_value = _ok_response()

        self._client().request("GET", "/stream", raw=True)

        row = self._queued()[0]
        self.assertEqual(row["state"], "success")
        self.assertEqual(row["status_code"], 200)
        self.assertIn("duration_ms", row)

    @patch("requests.Session.request")
    def test_a_raw_call_does_not_read_the_body(self, mock_request):
        response = _ok_response()
        mock_request.return_value = response

        self._client().request("GET", "/stream", raw=True)

        response.json.assert_not_called()
        self.assertEqual(self._queued()[0]["response_payload"], "null")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_raw_4xx_is_recorded_as_failed(self, mock_request):
        mock_request.return_value = _error_response(503, {"m": "down"})

        self._client().request("GET", "/stream", raw=True, raise_for_status=False)

        row = self._queued()[0]
        self.assertEqual(row["state"], "failed")
        self.assertEqual(row["status_code"], 503)
        self.assertEqual(row["error_type"], "server")


@tagged("post_install", "-at_install")
class TestErrorMessagesDoNotLeakCredentials(ClientLoggingCommon):
    TOKEN = "AAHsecretTOKENvalue"
    URL = f"https://vendor.invalid/file/xyz123456:{TOKEN}/photo.jpg"

    def setUp(self):
        super().setUp()
        from odoo.addons.integration.tools import api_client

        pattern = re.compile(r"xyz(\d+):([A-Za-z0-9_-]+)")
        api_client.register_url_secret(pattern, r"xyz\1:***REDACTED***")
        self.addCleanup(redact.REGISTERED_PATTERNS.pop)

    def _last_log(self):
        self.env.cr.precommit.run()
        return self.env["integration.exchange"].search([], order="id desc", limit=1)

    def test_an_unregistered_secret_shape_is_not_redacted(self):
        self.assertIn(
            "unregistered-secret",
            redact.mask_url("https://vendor.invalid/abc/unregistered-secret"),
        )

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_connection_error_does_not_store_the_token(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='vendor.invalid', port=443): "
            f"Max retries exceeded with url: /file/xyz123456:{self.TOKEN}"
            "/photo.jpg (Caused by NewConnectionError('failed to establish'))"
        )
        self.assertIn(
            self.TOKEN,
            str(mock_request.side_effect),
            "the fixture must actually carry the token, or this proves nothing",
        )

        with self.assertRaises(CommError) as caught:
            self._client().get(self.URL)

        self.assertNotIn(self.TOKEN, str(caught.exception))
        log = self._last_log()
        self.assertTrue(log, "the failure must still be recorded")
        self.assertNotIn(self.TOKEN, log.error_message or "")
        self.assertNotIn(self.TOKEN, log.request_url or "")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_timeout_does_not_store_the_token(self, mock_request):
        mock_request.side_effect = requests.exceptions.ReadTimeout(
            f"HTTPSConnectionPool: Read timed out for url: {self.URL}"
        )

        with self.assertRaises(CommError) as caught:
            self._client().get(self.URL)

        self.assertNotIn(self.TOKEN, str(caught.exception))
        self.assertNotIn(self.TOKEN, self._last_log().error_message or "")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_query_string_credential_is_masked_too(self, mock_request):
        url = "https://example.invalid/live?api_key=SUPERSECRETKEY&page=2"
        mock_request.side_effect = requests.exceptions.ConnectionError(
            f"Max retries exceeded with url: {url}"
        )

        with self.assertRaises(CommError):
            self._client().get(url)

        log = self._last_log()
        self.assertNotIn("SUPERSECRETKEY", log.error_message or "")
        self.assertIn("page=2", log.error_message or "", "only the secret goes")


@tagged("post_install", "-at_install")
class TestExternalExchangeLogging(ClientLoggingCommon):
    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    def test_it_records_a_successful_exchange(self):
        self._client().log_external_exchange(
            "POST", "https://pac.invalid/stamp", status_code=200, elapsed_ms=42
        )

        row = self._queued()[0]
        self.assertEqual(row["direction"], "outbound")
        self.assertEqual(row["status_code"], 200)
        self.assertEqual(row["state"], "success")
        self.assertEqual(row["duration_ms"], 42)

    def test_a_failure_is_recorded_as_failed(self):
        self._client().log_external_exchange(
            "POST", "https://pac.invalid/stamp", status_code=503, elapsed_ms=1
        )

        row = self._queued()[0]
        self.assertEqual(row["state"], "failed")
        self.assertEqual(row["error_type"], "server")

    def test_a_transport_error_with_no_status_is_a_network_failure(self):
        self._client().log_external_exchange(
            "POST", "https://pac.invalid/stamp", error="connection refused"
        )

        row = self._queued()[0]
        self.assertEqual(row["state"], "failed")
        self.assertEqual(row["error_type"], "network")

    def test_the_body_goes_through_the_same_redaction(self):
        self._client().log_external_exchange(
            "POST",
            "https://pac.invalid/stamp",
            request_body=json.dumps({"uuid": "abc-123", "password": SECRET_VALUE}),
            status_code=200,
        )

        payload = self._queued()[0]["request_payload"]
        self.assertIn("abc-123", payload)
        self.assertNotIn(SECRET_VALUE, payload)

    def test_a_credential_in_the_error_text_is_masked(self):
        self._client().log_external_exchange(
            "POST",
            "https://pac.invalid/stamp",
            error="failed calling https://pac.invalid/x?token=supersecrettoken",
        )

        self.assertNotIn("supersecrettoken", self._queued()[0]["error_message"])


@tagged("post_install", "-at_install")
class TestFailedExchangesAreRecordedAsFailed(ClientLoggingCommon):
    def _last_log(self):
        self.env.cr.precommit.run()
        return self.env["integration.exchange"].search([], order="id desc", limit=1)

    @staticmethod
    def _bodiless(status_code):
        response = MagicMock()
        response.status_code = status_code
        response.headers = {}
        response.text = ""
        response.json.side_effect = ValueError("no body")
        response.raise_for_status.return_value = None
        return response

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_bodiless_5xx_is_not_recorded_as_success(self, mock_request):
        mock_request.return_value = self._bodiless(502)

        result = self._client().get("/thing", raise_for_status=False)

        self.assertEqual(result["status_code"], 502)
        log = self._last_log()
        self.assertEqual(log.state, "failed")
        self.assertEqual(log.status_code, 502)
        self.assertEqual(log.error_type, "server", "failed rows need a kind too")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_bodiless_4xx_is_classified_by_status(self, mock_request):
        mock_request.return_value = self._bodiless(429)

        self._client().get("/thing", raise_for_status=False)

        log = self._last_log()
        self.assertEqual(log.state, "failed")
        self.assertEqual(log.error_type, "rate_limit")

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_2xx_is_still_a_success(self, mock_request):
        mock_request.return_value = _ok_response()

        self._client().get("/thing", raise_for_status=False)

        log = self._last_log()
        self.assertEqual(log.state, "success")
        self.assertFalse(log.error_type)


@tagged("post_install", "-at_install")
class TestDigestAuthAndTlsVerification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "Device operator",
                "category_id": cls.env.ref(
                    "credential.credential_category_basic_auth"
                ).id,
                "environment": "production",
                "username": "admin",
                "password": "device-pass",
            }
        )

    def _service(self, **overrides):
        vals = {
            "name": "Device probe",
            "code": "device_probe",
            "endpoint_url": "https://192.168.1.50",
            "auth_type": "digest",
            "environment": "production",
            **overrides,
        }
        service = self.env["integration.service"].create(vals)
        self.credential.endpoint_id = service
        return service

    def test_digest_auth_reaches_requests_as_a_challenge_handler(self):
        client = self._service()._get_api_client()

        self.assertIsInstance(client._get_auth(), HTTPDigestAuth)

    def test_a_non_digest_service_is_unaffected(self):
        client = self._service(code="basic_probe", auth_type="basic")._get_api_client()

        self.assertEqual(client._get_auth(), ("admin", "device-pass"))

    def test_a_service_that_authenticates_with_nothing_sends_nothing(self):
        client = self._service(code="none_probe", auth_type="none")._get_api_client()

        self.assertTrue(
            self.credential.get_basic_auth(),
            "the credential does carry a pair -- that is the point of the case",
        )
        self.assertIsNone(client._get_auth())

    def test_a_bearer_service_does_not_get_basic_auth_either(self):
        client = self._service(
            code="bearer_probe", auth_type="bearer"
        )._get_api_client()

        self.assertIsNone(client._get_auth())

    def test_verification_stays_on_by_default(self):
        self.assertTrue(self._service(code="default_probe").verify_tls)

    def test_verification_may_be_disabled_for_a_private_host(self):
        service = self._service(code="lan_probe", verify_tls=False)

        self.assertFalse(
            service._get_api_client()._get_tls_verification(
                "https://192.168.1.50/ISAPI/System/deviceInfo"
            )
        )

    def test_verification_may_not_be_disabled_for_a_public_host(self):
        with self.assertRaises(ValidationError):
            self._service(
                code="public_probe",
                endpoint_url="https://api.example.com",
                verify_tls=False,
            )

    def test_a_public_host_is_refused_at_request_time_too(self):
        client = self._service(code="lan_probe2", verify_tls=False)._get_api_client()

        with self.assertRaises(UserError):
            client._get_tls_verification("https://api.example.com/v1/things")


@tagged("post_install", "-at_install")
class TestRawResponsesBypassTheCache(ClientLoggingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cached_service = cls.env["integration.service"].create(
            {
                "name": "Cached probe",
                "code": "cached_probe",
                "endpoint_url": "https://example.invalid/live",
                "auth_type": "none",
                "environment": "production",
                "cache_enabled": True,
                "cache_ttl": 300,
            }
        )

    def _client(self):
        return self.cached_service._get_api_client()

    @patch("requests.Session.request")
    def test_a_raw_get_is_not_served_a_cached_dict(self, mock_request):
        mock_request.return_value = _ok_response()

        first = self._client().get("/thing")
        self.assertEqual(first["status_code"], 200)

        raw = self._client().get("/thing", raw=True)

        self.assertFalse(
            isinstance(raw, dict),
            "a raw caller was handed the cached parsed body",
        )
        self.assertTrue(hasattr(raw, "content"), "raw must return a live response")

    @patch("requests.Session.request")
    def test_the_cache_still_works_for_parsed_callers(self, mock_request):
        mock_request.return_value = _ok_response()

        self._client().get("/cached-thing")
        calls_after_first = mock_request.call_count
        self._client().get("/cached-thing")

        self.assertEqual(
            mock_request.call_count,
            calls_after_first,
            "the second parsed call should have been served from cache",
        )


@tagged("post_install", "-at_install")
class TestCallerSuppliedAuth(ClientLoggingCommon):
    @patch("requests.Session.request")
    def test_a_caller_may_pass_its_own_auth(self, mock_request):
        mock_request.return_value = _ok_response()

        self._client().get("/thing", auth=("device-user", "device-pass"))

        self.assertEqual(
            mock_request.call_args.kwargs["auth"], ("device-user", "device-pass")
        )

    @patch("requests.Session.request")
    def test_the_credential_is_still_the_default(self, mock_request):
        mock_request.return_value = _ok_response()

        self._client().get("/thing")

        self.assertIn("auth", mock_request.call_args.kwargs)
        self.assertIsNone(mock_request.call_args.kwargs["auth"])


@tagged("post_install", "-at_install")
class TestChainedCauseCarriesNoSecret(ClientLoggingCommon):
    LEAKY_URL = "https://example.invalid/live/stamp?access_token=" + SECRET_VALUE

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_an_http_error_cause_is_masked(self, mock_request):
        response = _error_response(400, SW_ALREADY_STAMPED)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"400 Client Error: Bad Request for url: {self.LEAKY_URL}",
            response=response,
        )
        mock_request.return_value = response

        with self.assertRaises(ClientError) as caught:
            self._client().post("/stamp", json={})

        self.assertNotIn(SECRET_VALUE, str(caught.exception.__cause__))
        self.assertIn("400 Client Error", str(caught.exception.__cause__))

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_network_error_cause_is_masked(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool: failed for url {self.LEAKY_URL}"
        )

        with self.assertRaises(CommError) as caught:
            self._client().post("/stamp", json={})

        self.assertNotIn(SECRET_VALUE, str(caught.exception.__cause__))

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_a_timeout_cause_is_masked(self, mock_request):
        mock_request.side_effect = requests.exceptions.Timeout(
            f"Read timed out for url {self.LEAKY_URL}"
        )

        with self.assertRaises(CommError) as caught:
            self._client().post("/stamp", json={})

        self.assertNotIn(SECRET_VALUE, str(caught.exception.__cause__))

    @mute_logger("odoo.addons.integration.tools.api_client")
    @patch("requests.Session.request")
    def test_the_whole_rendered_traceback_is_clean(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool: failed for url {self.LEAKY_URL}"
        )

        try:
            self._client().post("/stamp", json={})
        except CommError as e:
            rendered = "".join(traceback.format_exception(type(e), e, e.__traceback__))

        self.assertIn("ConnectionError", rendered, "the cause must still be reported")
        self.assertNotIn(SECRET_VALUE, rendered)


@tagged("post_install", "-at_install")
class TestRequestHeadersReachTheRow(ClientLoggingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odd_service = cls.env["integration.service"].create(
            {
                "name": "Odd Header Probe",
                "code": "odd_header_probe",
                "endpoint_url": "https://example.invalid/live",
                "auth_type": "api_key",
                "api_key_header": "X-Tenant-Ticket",
                "environment": "production",
            }
        )
        cls.env["credential.credential"].create(
            {
                "name": "Odd Header Credential",
                "endpoint_id": cls.odd_service.id,
                "company_id": cls.env.company.id,
                "category_id": cls.env.ref("credential.credential_category_custom").id,
                "environment": "production",
                "api_key": SECRET_VALUE,
            }
        )

    def _queued(self):
        return self.env.cr.precommit.data.get("integration.exchange.values") or []

    def _send(self, client=None, **call_kwargs):
        sent = {}

        def _record(*args, **kwargs):
            sent.update(kwargs)
            return _ok_response()

        with patch("requests.Session.request", side_effect=_record):
            (client or self._client()).post("/probe", **call_kwargs)
        return sent.get("headers"), self._queued()[0]

    def test_the_row_describes_the_headers_that_were_sent(self):
        sent, row = self._send(headers={"Content-Type": "application/xml"})

        self.assertTrue(sent, "the test sent no headers at all")
        self.assertEqual(set(row["request_headers"]), set(sent))

    def test_a_row_without_secrets_is_still_worth_keeping(self):
        _sent, row = self._send(headers={"Content-Type": "application/xml"})

        self.assertEqual(row["request_headers"]["Content-Type"], "application/xml")

    def test_a_caller_authorization_header_is_redacted(self):
        _sent, row = self._send(headers={"Authorization": f"Bearer {SECRET_VALUE}"})

        self.assertEqual(row["request_headers"]["Authorization"], "***REDACTED***")
        self.assertNotIn(SECRET_VALUE, str(row))

    def test_a_hyphenated_header_name_reaches_the_denylist(self):
        _sent, row = self._send(headers={"X-API-Key": SECRET_VALUE})

        self.assertEqual(row["request_headers"]["X-API-Key"], "***REDACTED***")
        self.assertNotIn(SECRET_VALUE, str(row))

    def test_a_credential_header_with_an_unguessable_name_is_redacted(self):
        client = self.odd_service._get_api_client()
        _sent, row = self._send(client=client)

        self.assertEqual(row["request_headers"]["X-Tenant-Ticket"], "***REDACTED***")
        self.assertNotIn(SECRET_VALUE, str(row))

    def test_provenance_does_not_redact_the_whole_row(self):
        client = self.odd_service._get_api_client()
        _sent, row = self._send(client=client, headers={"Accept-Language": "es-MX"})

        self.assertEqual(row["request_headers"]["Accept-Language"], "es-MX")


@tagged("post_install", "-at_install")
class TestCredentialChangesDropCachedSessions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Session probe",
                "code": "session_probe",
                "endpoint_url": "https://example.invalid/live",
                "auth_type": "api_key",
                "environment": "production",
            }
        )
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "Session probe key",
                "category_id": cls.env.ref("credential.credential_category_api_key").id,
                "environment": "production",
                "api_key": "first-key",
                "endpoint_id": cls.service.id,
            }
        )

    def _cached_keys(self):
        from odoo.addons.integration.tools.session_cache import get_session_cache

        cached = get_session_cache(self.env).keys()
        return [key for key in cached if key.startswith(f"{self.service.code}:")]

    def test_rotating_the_secret_drops_the_services_cached_sessions(self):
        self.service._get_api_client()._get_or_create_session()
        self.assertTrue(self._cached_keys(), "precondition: a session is cached")

        self.credential.api_key = "rotated-key"

        self.assertEqual(self._cached_keys(), [])

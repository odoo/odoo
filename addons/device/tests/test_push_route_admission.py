import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import DeviceHttpCase


@tagged("post_install", "-at_install")
class TestPushRouteAdmission(DeviceHttpCase):
    """The push route is admitted by the device's gate: the exchange row is
    the call's record, a copy inside the window is refused on that row, and
    a call the handler could not finish still leaves one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Admission Config")
        cls.device = cls._create_device_device(
            config=cls.config,
            name="Admission Device",
            identifier="ADMIT-1",
            endpoint="10.0.0.11",
            processing_mode="sync",
        )
        cls.token = cls._device_token(cls.device)

    def _push(self, body=None, token=None, identifier=None):
        self.env.flush_all()
        return self.url_open(
            f"/remote/device/{identifier or self.device.identifier}/data",
            data=body if body is not None else json.dumps({"t": 1}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token or self.token}",
            },
        )

    def _rows(self, device=None):
        return self.env["integration.exchange"].search(
            [("channel_id", "=", f"device.device,{(device or self.device).id}")],
            order="id",
        )

    def test_an_admitted_push_is_one_row_holding_the_body(self):
        response = self._push(json.dumps({"temperature": 21.5}).encode())

        self.assertEqual(response.status_code, 200)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, "success")
        self.assertEqual(row.event_type, "device_push")
        self.assertEqual(row.request_method, "POST")
        self.assertIn("21.5", row.request_payload)
        self.assertTrue(row.request_payload_hash)

    def test_a_copy_inside_the_window_is_refused_on_its_own_row(self):
        self.device.write(
            {"duplicate_detection_enabled": True, "duplicate_window_seconds": 60}
        )
        body = json.dumps({"reading": 7}).encode()

        first = self._push(body)
        second = self._push(json.dumps({"reading": 7}, indent=2).encode())

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"], "duplicate_event")
        rows = self._rows()
        self.assertEqual(rows.mapped("state"), ["success", "duplicate"])
        self.assertEqual(len(set(rows.mapped("request_payload_hash"))), 1)

    def test_a_body_that_is_not_json_is_refused_after_admission(self):
        response = self._push(b"not json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_json")
        row = self._rows()
        self.assertEqual(row.state, "failed")
        self.assertIn("JSON", row.error_message)

    @mute_logger("odoo.addons.device.controllers.main")
    def test_a_handler_failure_is_a_failed_row_kept_for_retry(self):
        Device = type(self.env["device.device"])
        body = json.dumps(
            {"reading": 7, "url": "https://h.invalid/?token=abc", "note": "x" * 5000}
        ).encode()
        with patch.object(
            Device, "_store_push_data_point", side_effect=RuntimeError("boom")
        ):
            response = self._push(body)

        self.assertEqual(response.status_code, 500)
        row = self._rows()
        self.assertEqual(row.state, "retry", "a failed push is scheduled for a retry")
        self.assertIn("boom", row.error_message)
        self.assertEqual(
            row.get_payload_dict(),
            json.loads(body),
            "the retry replays the body as received, not the redacted log copy",
        )

    def test_an_empty_size_limit_is_the_default_not_zero_bytes(self):
        # a device that predates the column's default holds NULL there
        self.env.cr.execute(
            "UPDATE device_device SET max_payload_size = NULL WHERE id = %s",
            [self.device.id],
        )
        self.device.invalidate_recordset(["max_payload_size"])

        response = self._push(json.dumps({"reading": 1}).encode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._rows().state, "success")

    def test_a_wrong_token_leaves_no_row(self):
        response = self._push(token="not-the-token")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(self._rows())

    def test_an_unknown_identifier_is_recorded_as_an_unknown_caller(self):
        response = self._push(identifier="NOBODY")

        self.assertEqual(response.status_code, 404)
        row = self.env["integration.exchange"].search(
            [
                ("state", "=", "refused"),
                ("refusal_reason", "=", "endpoint_not_found"),
                ("channel_name", "like", "device.device:%"),
            ]
        )
        self.assertEqual(len(row), 1)
        self.assertIn("NOBODY", row.channel_name)

    def test_the_token_picks_the_device_when_two_companies_share_an_identifier(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        twin = self._create_device_device(
            config=self.config,
            name="Twin",
            identifier=self.device.identifier,
            company_id=other_company.id,
            processing_mode="sync",
        )
        twin_token = self._device_token(twin)

        response = self._push(token=twin_token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["device_name"], "Twin")
        self.assertEqual(len(self._rows(twin)), 1)
        self.assertFalse(self._rows())

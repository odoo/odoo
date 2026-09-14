import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestBoxEnrolment(HttpCase):
    """``/iot/setup`` is the only route a box calls before it is known."""

    def _setup(self, iot_box, devices):
        response = self.url_open(
            "/iot/setup",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"params": {"iot_box": iot_box, "devices": devices}}),
        )
        return response.json()["result"]

    def _payload(self, token, identifier="test_enrol_box"):
        return {
            "identifier": identifier,
            "ip": "10.0.0.9",
            "version": "L25.07",
            "token": token,
        }

    def _hand_out_token(self):
        token = "0123456789abcdef"
        self.env["ir.config_parameter"].sudo().set_param("iot.iot_token", token)
        return token

    def _box(self):
        return (
            self.env["iot.box"]
            .sudo()
            .search([("identifier", "=", "test_enrol_box")], limit=1)
        )

    def test_a_box_with_the_wrong_token_does_not_enrol_itself(self):
        self._hand_out_token()
        self.assertIsNone(self._setup(self._payload("not-the-token"), {}))
        self.assertFalse(self._box(), "an unknown box must not enrol on a bad token")

    def test_a_token_older_than_its_validity_does_not_enrol_a_box(self):
        token = self._hand_out_token()
        self.env.cr.execute(
            "UPDATE ir_config_parameter SET write_date = now() at time zone 'UTC' "
            "- interval '16 minutes' WHERE key = 'iot.iot_token'"
        )
        self.env["ir.config_parameter"].invalidate_model()

        self.assertIsNone(self._setup(self._payload(token), {}))
        self.assertFalse(self._box(), "a stale pairing token must not enrol a box")

    def test_the_token_is_spent_by_the_box_that_used_it(self):
        token = self._hand_out_token()
        self.assertTrue(self._setup(self._payload(token), {}))
        self.assertTrue(self._box(), "the box should have been created")
        self.assertFalse(
            self.env["ir.config_parameter"].sudo().get_param("iot.iot_token"),
            "the token must be cleared so the next box cannot reuse it",
        )

    def test_a_device_the_box_stops_reporting_is_marked_disconnected(self):
        token = self._hand_out_token()
        two = {
            "printer_a": {
                "name": "Printer A",
                "type": "printer",
                "connection": "network",
            },
            "scale_b": {"name": "Scale B", "type": "scale", "connection": "serial"},
        }
        self._setup(self._payload(token), two)
        self._setup(self._payload(token), {"printer_a": two["printer_a"]})
        devices = self._box().device_ids
        self.assertEqual(len(devices), 2, "the absent device is kept, not deleted")
        by_identifier = {d.identifier: d.connected_status for d in devices}
        self.assertEqual(by_identifier["printer_a"], "connected")
        self.assertEqual(by_identifier["scale_b"], "disconnected")

    def test_a_fiscal_data_module_that_changes_port_keeps_one_record(self):
        """A serial device is identified by its port, so replugging it reads as
        a new device. ``_find_moved_device`` is what stops the duplicate."""
        token = self._hand_out_token()
        blackbox = {
            "name": "BODO001 fiscal data module",
            "type": "fiscal_data_module",
            "connection": "serial",
        }
        self._setup(self._payload(token), {"serial_ttyS0": blackbox})
        self._setup(self._payload(token), {"serial_ttyS1": blackbox})
        devices = self._box().device_ids
        self.assertEqual(
            len(devices),
            1,
            "the moved fiscal data module should be re-pointed, not duplicated",
        )
        self.assertEqual(devices.identifier, "serial_ttyS1")
        self.assertEqual(devices.connected_status, "connected")

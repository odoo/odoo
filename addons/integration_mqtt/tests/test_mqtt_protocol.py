from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt

from odoo.tests import BaseCase, tagged

from ..tools import mqtt_protocol
from odoo.addons.integration.tools.stream_protocol import (
    STREAM_PROTOCOLS,
    StreamSnapshot,
)


def _snapshot(url="mqtt://broker.example:1883", **overrides):
    values = {
        "id": 7,
        "db_name": "probe",
        "name": "Scale",
        "protocol": "mqtt",
        "url": url,
        "secret": "s3cret",
        "login": "scale",
        "subscriptions": {"topics": ["scale/+/weight", "scale/status"]},
        "heartbeat_seconds": 30,
        "options": {"qos": 2, "client_id": "scale-7", "publish_topic": "scale/7/cmd"},
        "addresses": ("10.0.0.9",),
    }
    values.update(overrides)
    return StreamSnapshot(**values)


@tagged("post_install", "-at_install", "integration")
class TestMqttProtocol(BaseCase):
    def setUp(self):
        super().setUp()
        self.client = MagicMock()
        self.client.is_connected.return_value = True
        publish_info = MagicMock(rc=mqtt.MQTT_ERR_SUCCESS)
        self.client.publish.return_value = publish_info
        patcher = patch.object(mqtt_protocol.mqtt, "Client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.protocol = mqtt_protocol.MqttProtocol()
        self.frames = []
        self.states = []

    def _open(self, snapshot=None):
        return self.protocol.open(
            snapshot or _snapshot(),
            lambda payload, meta: self.frames.append((payload, dict(meta))),
            lambda state, message: self.states.append((state, message)),
        )

    def test_the_protocol_is_registered_under_mqtt(self):
        self.assertIs(STREAM_PROTOCOLS["mqtt"], mqtt_protocol.MqttProtocol)
        self.assertEqual(mqtt_protocol.MqttProtocol.schemes, ("mqtt", "mqtts"))

    def test_a_plain_session_dials_the_pinned_address_with_the_credential(self):
        self._open()
        mqtt_protocol.mqtt.Client.assert_called_once()
        self.assertEqual(
            mqtt_protocol.mqtt.Client.call_args.kwargs["client_id"], "scale-7"
        )
        self.client.username_pw_set.assert_called_once_with("scale", "s3cret")
        self.client.tls_set_context.assert_not_called()
        host, port = self.client.connect.call_args.args
        self.assertEqual(
            (host, port), ("10.0.0.9", 1883), "the address ir.egress pinned"
        )
        self.assertEqual(self.client.connect.call_args.kwargs["keepalive"], 30)
        self.client.loop_start.assert_called_once()

    def test_a_tls_session_dials_by_name_so_the_certificate_is_checked(self):
        self._open(_snapshot(url="mqtts://broker.example"))
        self.client.tls_set_context.assert_called_once()
        host, port = self.client.connect.call_args.args
        self.assertEqual((host, port), ("broker.example", 8883))

    def test_connecting_subscribes_the_topics_and_says_open(self):
        handle = self._open()
        self.client.on_connect(self.client, None, MagicMock(), 0, None)
        self.assertEqual(
            [call.args for call in self.client.subscribe.call_args_list],
            [("scale/+/weight", 2), ("scale/status", 2)],
        )
        self.assertEqual(self.states, [("open", None)])
        self.assertTrue(handle.connected.is_set())

    def test_a_refused_connection_is_an_error_state_and_stops_paho_s_redial(self):
        self._open()
        self.client.on_connect(self.client, None, MagicMock(), 5, None)
        self.assertEqual(self.states[0][0], "error")
        self.assertIn("5", self.states[0][1])
        self.client.disconnect.assert_called_once()

    def test_a_tls_session_presents_the_stream_s_material(self):
        with patch.object(mqtt_protocol, "tls_context", return_value="ctx") as builder:
            snapshot = _snapshot(url="mqtts://broker.example")
            self._open(snapshot)
        builder.assert_called_once_with(snapshot)
        self.client.tls_set_context.assert_called_once_with("ctx")

    def test_a_message_is_a_frame_with_its_topic(self):
        self._open()
        message = MagicMock(
            payload=b'{"kg": 12.5}', topic="scale/7/weight", qos=1, retain=False
        )
        self.client.on_message(self.client, None, message)
        self.assertEqual(
            self.frames,
            [(b'{"kg": 12.5}', {"topic": "scale/7/weight", "qos": 1, "retain": False})],
        )

    def test_an_unexpected_disconnect_asks_for_a_redial(self):
        handle = self._open()
        handle.connected.set()
        self.client.on_disconnect(self.client, None, MagicMock(), 7, None)
        self.assertFalse(handle.connected.is_set())
        self.assertEqual(self.states[-1][0], "backoff")

    def test_a_send_publishes_on_the_frame_s_topic_or_the_stream_s(self):
        handle = self._open()
        self.protocol.send(handle, b"tare", {"topic": "scale/7/do", "qos": 0})
        self.protocol.send(handle, b"zero", {})
        calls = self.client.publish.call_args_list
        self.assertEqual(calls[0].args, ("scale/7/do", b"tare"))
        self.assertEqual(calls[0].kwargs["qos"], 0)
        self.assertEqual(calls[1].args, ("scale/7/cmd", b"zero"))
        self.assertEqual(
            calls[1].kwargs["qos"], 2, "the stream's QoS when the frame names none"
        )

    def test_a_send_with_no_topic_anywhere_is_refused(self):
        handle = self._open(_snapshot(options={"qos": 1}))
        with self.assertRaises(ValueError):
            self.protocol.send(handle, b"x", {})

    def test_a_publish_the_client_refuses_raises(self):
        handle = self._open()
        self.client.publish.return_value = MagicMock(rc=mqtt.MQTT_ERR_NO_CONN)
        with self.assertRaises(OSError):
            self.protocol.send(handle, b"x", {"topic": "t"})

    def test_alive_is_the_client_s_word(self):
        handle = self._open()
        self.assertTrue(self.protocol.alive(handle))
        self.client.is_connected.return_value = False
        self.assertFalse(self.protocol.alive(handle))

    def test_closing_disconnects_and_stops_the_loop(self):
        handle = self._open()
        self.protocol.close(handle)
        self.client.disconnect.assert_called_once()
        self.client.loop_stop.assert_called_once()

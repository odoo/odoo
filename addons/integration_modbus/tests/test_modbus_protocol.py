import json
import threading
from unittest.mock import MagicMock, patch

from odoo.tests import BaseCase, tagged

from ..tools import modbus_protocol
from odoo.addons.integration.tools.stream_protocol import (
    STREAM_PROTOCOLS,
    StreamSnapshot,
)


def _snapshot(url="modbus://plc.example:5020", **overrides):
    values = {
        "id": 9,
        "db_name": "probe",
        "name": "PLC",
        "protocol": "modbus",
        "url": url,
        "secret": None,
        "login": None,
        "subscriptions": {
            "unit_id": 3,
            "registers": [
                {"type": "holding", "start": 100, "count": 2},
                {"type": "coil", "start": 0, "count": 3},
            ],
        },
        "heartbeat_seconds": 30,
        "options": {"timeout": 2},
        "addresses": ("10.0.0.7",),
    }
    values.update(overrides)
    return StreamSnapshot(**values)


class _Result:
    def __init__(self, registers=None, bits=None, error=False):
        self.registers = registers or []
        self.bits = bits or []
        self._error = error

    def isError(self):
        return self._error


@tagged("post_install", "-at_install", "integration")
class TestModbusProtocol(BaseCase):
    def setUp(self):
        super().setUp()
        self.client = MagicMock()
        self.client.connect.return_value = True
        self.client.connected = True
        self.client.read_holding_registers.return_value = _Result(registers=[11, 22])
        self.client.read_coils.return_value = _Result(bits=[True, False, True, False])
        self.client.write_register.return_value = _Result()
        self.client.write_coils.return_value = _Result()
        tcp = patch.object(modbus_protocol, "ModbusTcpClient", return_value=self.client)
        serial = patch.object(
            modbus_protocol, "ModbusSerialClient", return_value=self.client
        )
        tcp.start()
        serial.start()
        self.addCleanup(tcp.stop)
        self.addCleanup(serial.stop)
        self.protocol = modbus_protocol.ModbusProtocol()
        self.frames = []
        self.states = []
        self.handles = []

    def tearDown(self):
        for handle in self.handles:
            handle.stop.set()
            if handle.thread is not None:
                handle.thread.join(timeout=2)
        super().tearDown()

    def _open(self, snapshot=None, wait=True):
        polled = threading.Event()

        def on_frame(payload, meta):
            self.frames.append((json.loads(payload), dict(meta)))
            if len(self.frames) >= 2:
                polled.set()

        handle = self.protocol.open(
            snapshot or _snapshot(),
            on_frame,
            lambda state, message: self.states.append((state, message)),
        )
        self.handles.append(handle)
        if wait:
            self.assertTrue(polled.wait(5), "the first poll happens at once")
        return handle

    def test_the_protocol_is_registered_under_modbus(self):
        self.assertIs(STREAM_PROTOCOLS["modbus"], modbus_protocol.ModbusProtocol)
        self.assertEqual(
            modbus_protocol.ModbusProtocol.schemes, ("modbus", "modbus+rtu")
        )

    def test_a_tcp_link_dials_the_pinned_address(self):
        self._open()
        kwargs = modbus_protocol.ModbusTcpClient.call_args.kwargs
        self.assertEqual(
            (kwargs["host"], kwargs["port"], kwargs["timeout"]), ("10.0.0.7", 5020, 2.0)
        )
        self.client.connect.assert_called_once()

    def test_a_serial_link_opens_the_port_at_its_baud_rate(self):
        self._open(
            _snapshot(url="modbus+rtu:///dev/ttyUSB0?baudrate=19200", addresses=())
        )
        kwargs = modbus_protocol.ModbusSerialClient.call_args.kwargs
        self.assertEqual((kwargs["port"], kwargs["baudrate"]), ("/dev/ttyUSB0", 19200))

    def test_a_link_that_does_not_connect_refuses_to_open(self):
        self.client.connect.return_value = False
        with self.assertRaises(ConnectionError):
            self._open(wait=False)

    def test_the_first_poll_reads_every_block_as_a_frame(self):
        self._open()
        self.assertEqual(self.states[0], ("open", None))
        holding, coils = self.frames
        self.assertEqual(
            holding[0],
            {
                "unit_id": 3,
                "register_type": "holding",
                "start_address": 100,
                "count": 2,
                "values": [11, 22],
            },
        )
        self.assertEqual(holding[1]["topic"], "holding/100")
        self.assertEqual(coils[0]["values"], [True, False, True])
        self.client.read_holding_registers.assert_called_with(100, count=2, device_id=3)
        self.client.read_coils.assert_called_with(0, count=3, device_id=3)

    def test_a_failed_read_asks_for_a_redial_and_ends_the_poll(self):
        self.client.read_holding_registers.return_value = _Result(error=True)
        handle = self._open(wait=False)
        handle.thread.join(timeout=5)
        self.assertFalse(handle.thread.is_alive())
        self.assertEqual(self.states[-1][0], "backoff")
        self.assertFalse(self.protocol.alive(handle))

    def test_a_send_writes_a_register_or_coils(self):
        handle = self._open()
        self.protocol.send(
            handle, json.dumps({"address": 40, "value": 7, "unit_id": 3}).encode(), {}
        )
        self.protocol.send(
            handle,
            json.dumps(
                {"type": "coil", "address": 1, "values": [True, False]}
            ).encode(),
            {},
        )
        self.client.write_register.assert_called_once_with(40, 7, device_id=3)
        self.client.write_coils.assert_called_once_with(1, [True, False], device_id=1)

    def test_a_refused_write_raises(self):
        handle = self._open()
        self.client.write_register.return_value = _Result(error=True)
        with self.assertRaises(OSError):
            self.protocol.send(
                handle, json.dumps({"address": 1, "value": 1}).encode(), {}
            )

    def test_closing_stops_the_poll_and_the_link(self):
        handle = self._open()
        self.protocol.close(handle)
        self.assertFalse(handle.thread.is_alive())
        self.client.close.assert_called_once()

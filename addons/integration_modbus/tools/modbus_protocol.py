import json
import logging
import threading
from urllib.parse import parse_qs, urlsplit

from pymodbus.client import ModbusSerialClient, ModbusTcpClient

from odoo.addons.integration.tools.stream_protocol import StreamProtocol, register

_logger = logging.getLogger(__name__)

_READERS = {
    "holding": ("read_holding_registers", "registers"),
    "input": ("read_input_registers", "registers"),
    "coil": ("read_coils", "bits"),
    "discrete": ("read_discrete_inputs", "bits"),
}

_MAX_COUNT = 125


class ModbusHandle:
    __slots__ = ("client", "failing", "lock", "stop", "stream", "thread")

    def __init__(self, client, stream):
        self.client = client
        self.stream = stream
        self.stop = threading.Event()
        self.thread = None
        self.lock = threading.Lock()
        self.failing = False


@register
class ModbusProtocol(StreamProtocol):
    key = "modbus"
    label = "Modbus"
    schemes = ("modbus", "modbus+rtu")

    def open(self, stream, on_frame, on_state):
        url = urlsplit(stream.url)
        options = stream.options
        timeout = float(options.get("timeout", 10))
        if url.scheme == "modbus+rtu":
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            client = ModbusSerialClient(
                port=url.path,
                baudrate=int(query.get("baudrate", options.get("baudrate", 9600))),
                timeout=timeout,
            )
        else:
            client = ModbusTcpClient(  # noqa: E8518 - the address was checked by ir.egress on the snapshot; Modbus is a bare TCP frame protocol with nothing to pin
                host=stream.addresses[0] if stream.addresses else url.hostname,
                port=url.port or 502,
                timeout=timeout,
            )
        if not client.connect():
            raise ConnectionError(f"Modbus did not connect to {stream.url}")
        handle = ModbusHandle(client, stream)
        registers = list((stream.subscriptions or {}).get("registers") or [])
        unit_id = int(
            (stream.subscriptions or {}).get("unit_id", options.get("unit_id", 1))
        )

        def poll():
            on_state("open", None)
            delay = 0
            while not handle.stop.wait(delay):
                delay = stream.heartbeat_seconds
                for block in registers:
                    try:
                        with handle.lock:
                            reading = self._read(client, block, unit_id)
                    except Exception as error:
                        handle.failing = True
                        on_state("backoff", f"{type(error).__name__}: {error}")
                        return
                    on_frame(
                        json.dumps(reading).encode(),
                        {"topic": _topic(block), **reading_meta(block)},
                    )
                handle.failing = False

        handle.thread = threading.Thread(
            target=poll, name=f"odoo.stream.modbus.{stream.id}", daemon=True
        )
        handle.thread.start()
        return handle

    @staticmethod
    def _read(client, block, unit_id):
        method_name, attribute = _READERS.get(
            block.get("type", "holding"), _READERS["holding"]
        )
        start = int(block.get("start", 0))
        count = min(int(block.get("count", 1)), _MAX_COUNT)
        result = getattr(client, method_name)(
            start, count=count, device_id=int(block.get("unit_id", unit_id))
        )
        if result.isError():
            raise OSError(f"Modbus read error: {result}")
        values = list(getattr(result, attribute))[:count]
        return {
            "unit_id": int(block.get("unit_id", unit_id)),
            "register_type": block.get("type", "holding"),
            "start_address": start,
            "count": count,
            "values": values,
        }

    def send(self, handle, payload, meta):
        frame = json.loads(payload)
        address = int(frame.get("address", meta.get("address", 0)))
        unit_id = int(frame.get("unit_id", meta.get("unit_id", 1)))
        values = frame.get("values", frame.get("value"))
        kind = frame.get("type", meta.get("type", "holding"))
        with handle.lock:
            if kind == "coil":
                result = (
                    handle.client.write_coils(address, values, device_id=unit_id)
                    if isinstance(values, list)
                    else handle.client.write_coil(
                        address, bool(values), device_id=unit_id
                    )
                )
            else:
                result = (
                    handle.client.write_registers(address, values, device_id=unit_id)
                    if isinstance(values, list)
                    else handle.client.write_register(
                        address, int(values), device_id=unit_id
                    )
                )
        if result.isError():
            raise OSError(f"Modbus write error: {result}")

    def alive(self, handle):
        return (
            not handle.failing
            and handle.thread is not None
            and handle.thread.is_alive()
            and bool(handle.client.connected)
        )

    def close(self, handle):
        handle.stop.set()
        if handle.thread is not None:
            handle.thread.join(timeout=5)
        with handle.lock:
            handle.client.close()


def _topic(block):
    return f"{block.get('type', 'holding')}/{int(block.get('start', 0))}"


def reading_meta(block):
    return {
        "register_type": block.get("type", "holding"),
        "start": int(block.get("start", 0)),
    }

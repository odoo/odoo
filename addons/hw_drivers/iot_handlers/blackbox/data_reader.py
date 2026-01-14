import threading

from serial.threaded import Protocol
from .helpers import log


STX = 0x02
ETX = 0x03
ACK = 0x06
NACK = 0x15
T1_MAX = 0.3
T2_MAX = 0.75
RETRY_MAX = 3


class DataReader(Protocol):
    def __init__(self):
        super().__init__()
        self.buffer = bytearray()

        # key -> {"event": threading.Event, "response": str | None}
        self._on_stop_callbacks = []
        self._pending = {}
        self._pending_lock = threading.Lock()

    def connection_lost(self, exc):
        log('error', 'DataReader', f'Connection lost with {self.transport.serial.port}')
        for callback in self._on_stop_callbacks:
            callback()
        super().connection_lost(exc)

    def connection_made(self, transport):
        self.transport = transport
        log('success', 'DataReader', f'Connection made with {self.transport.serial.port}')

    def data_received(self, data):
        self.buffer.extend(data)
        length = len(data)
        log("debug", "DataReader", f"Packet from {self.transport.serial.port}: length {length}")
        self._process_buffer()

    def write_line(self, text: str):
        value = self.build_frame(text)
        self.transport.write(value)

    def _process_buffer(self):
        while True:
            # strip leading ACK/NACK
            while self.buffer and self.buffer[0] in (ACK, NACK):
                ctrl = self.buffer.pop(0)
                if ctrl == ACK:
                    log("debug", "DataReader", f"ACK received from {self.transport.serial.port}")
                else:
                    log("warning", "DataReader", f"NACK received from {self.transport.serial.port}")

            if not self.buffer:
                return

            try:
                stx_index = self.buffer.index(STX)
            except ValueError:
                self.buffer.clear()
                return

            if stx_index > 0:
                del self.buffer[:stx_index]

            if len(self.buffer) < 3:
                return

            try:
                etx_index = self.buffer.index(ETX, 1)
            except ValueError:
                return

            if etx_index + 1 >= len(self.buffer):
                return

            frame = self.buffer[:etx_index + 2]   # STX..ETX+BCC
            del self.buffer[:etx_index + 2]
            self._handle_frame(frame)

    def _handle_frame(self, frame: bytes):
        if frame[0] != STX:
            log("warning", "DataReader", f"Frame without STX: {frame!r}")
            self.transport.write(bytes([NACK]))
            return

        etx_pos = frame.rfind(ETX)
        if etx_pos == -1 or etx_pos + 1 >= len(frame):
            log("warning", "DataReader", f"Frame without ETX/LRC: {frame!r}")
            self.transport.write(bytes([NACK]))
            return

        data = frame[1:etx_pos]
        bcc = frame[etx_pos + 1]
        calc = self.compute_lrc(data)

        if bcc != calc:
            log("warning", "DataReader", f"Bad LRC: got {bcc:#02x}, expected {calc:#02x}")
            self.transport.write(bytes([NACK]))
            return

        self.transport.write(bytes([ACK]))

        text = data.decode("ascii", errors="ignore")
        identifier = text[0]
        seq_str = text[1:3]
        key = f"{identifier}{seq_str}"
        text = data.decode('ascii', errors='ignore')
        log("debug", "DataReader", f"Valid frame from {self.transport.serial.port}: {text!r}")

        # Resolve any pending waiter
        with self._pending_lock:
            entry = self._pending.get(key)

        if entry:
            entry["response"] = text
            entry["event"].set()
        else:
            log("warning", "DataReader", f"No waiter for key {key}, payload={text!r}")

    @staticmethod
    def compute_lrc(msg: bytes) -> int:
        lrc = 0
        for b in msg:
            lrc = (lrc + b) & 0xFF
        return ((lrc ^ 0xFF) + 1) & 0xFF

    def build_frame(self, payload: str) -> bytes:
        data = payload.encode('ascii')
        bcc = self.compute_lrc(data)
        return bytes([STX]) + data + bytes([ETX, bcc])

    def _send_once_and_wait(self, text: str, timeout: float) -> str:
        """
        Send a payload (already formatted as header+body) and wait
        for the response with the same identifier+sequence.

        Raises TimeoutError on timeout.
        """
        identifier = text[0]
        seq_str = text[1:3]
        key = f"{identifier}{seq_str}"

        evt = threading.Event()
        with self._pending_lock:
            self._pending[key] = {"event": evt, "response": None}

        self.write_line(text)

        if not evt.wait(timeout):
            with self._pending_lock:
                self._pending.pop(key, None)
            raise TimeoutError(f"No response for {key} within {timeout} s")

        with self._pending_lock:
            entry = self._pending.pop(key, None)

        if not entry or entry["response"] is None:
            raise RuntimeError(f"Response for {key} lost")

        return entry["response"]

    def send_and_wait(self, cmd: str, seq: int, data: str = "", timeout: float = T2_MAX, max_retries: int = RETRY_MAX) -> str:
        """
        Send a command with header+body, wait for a response, retry up to
        max_retries if we get no response (timeout).
        - cmd: 1-char identifier, e.g. 'I', 'H', ...
        - seq: 0..99, will be zero-padded to 2 digits
        - body: rest of the payload (after the 4-char header)
        """
        last_err = None
        for retry in range(0, max_retries + 1):
            try:
                log("debug", "DataReader", f"Sending {cmd} seq={seq:02d} retry={retry} body={data!r}")
                header = f"{cmd}{seq:02d}{retry}"
                return self._send_once_and_wait(header + data, timeout)
            except TimeoutError as e:
                last_err = e
                log("warning", "DataReader", f"Timeout for {cmd}{seq:02d} retry={retry}, {'giving up' if retry >= max_retries else 'retrying'}")

        # All attempts failed
        raise last_err or TimeoutError(f"No response after {max_retries + 1} attempts")

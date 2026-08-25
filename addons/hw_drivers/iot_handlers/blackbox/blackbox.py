import threading
import time
import serial

from serial.tools import list_ports
from serial.threaded import ReaderThread, LineReader

from .helpers import log, BlackboxError, parse_fdm_log
from .data_reader import DataReader


RETRY_MAX = 3
AVAILABLE_COMMANDS = ["H", "I", "P", "S", "O"]


class Blackbox:
    def __init__(self):
        self.scanning = False
        self.readers: dict[str, DataReader] = {}
        self.protocols: dict[str, LineReader] = {}
        self.blackboxes: dict[str, DataReader] = {}
        self.sequences: dict[str, int] = {cmd: 0 for cmd in AVAILABLE_COMMANDS}
        self.sequence_number: dict[str, int] = {cmd: 0 for cmd in AVAILABLE_COMMANDS}
        self._start_periodic_rescan()

    def _start_periodic_rescan(self):
        def loop():
            while True:
                self.init()
                time.sleep(10.0)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def init(self) -> None:
        """Scan serial ports and initialize compatible FDMs."""
        if self.scanning:
            log("debug", "Blackbox", "Already scanning, skipping init.")
            return

        self.scanning = True

        try:
            port_list = list_ports.comports()

            for info in port_list:
                path = info.device  # same as info.path in your TS code

                if path in self.readers:
                    continue

                ser = serial.Serial()
                ser.port = path
                ser.baudrate = 19200
                ser.bytesize = serial.EIGHTBITS
                ser.stopbits = serial.STOPBITS_ONE
                ser.parity = serial.PARITY_NONE
                ser.rtscts = False
                ser.xonxoff = False
                ser.timeout = 0.2

                try:
                    ser.open()
                    self.bind_listeners(ser)
                    result = self.protocols[ser.port].send_and_wait("I", 1)
                    parse_fdm_log(result)
                    fdm_id = result[10:21]

                    if fdm_id in self.blackboxes:
                        log("warning", "Blackbox", f"FDM ID {fdm_id} already registered, skipping.")
                        continue

                    self.blackboxes[fdm_id] = self.protocols[ser.port]
                    self.protocols[ser.port]._on_stop_callbacks.append(lambda: self.blackboxes.pop(fdm_id, None))
                    log("success", "Blackbox", f"Initialized FDM with ID {fdm_id} on port {path}")
                except (serial.SerialException, OSError) as e:
                    log("error", path, "Initialization error")
                    log("debug", path, f"{e}")
        finally:
            self.scanning = False

    def bind_listeners(self, ser: serial.Serial) -> None:
        reader_thread = ReaderThread(ser, DataReader)
        reader_thread.start()

        while reader_thread.protocol is None:
            time.sleep(0.01)

        protocol = reader_thread.protocol
        self.readers[ser.port] = reader_thread
        self.protocols[ser.port] = protocol
        protocol._on_stop_callbacks.append(lambda: self.readers.pop(ser.port, None))
        protocol._on_stop_callbacks.append(lambda: self.protocols.pop(ser.port, None))

        log("debug", "Blackbox", f"ReaderThread started for {ser.port}")

    def send(self, id, cmd, data="") -> str:
        if not self.blackboxes.get(id):
            raise BlackboxError(f"Blackbox with ID {id} not found.", 404)

        seq = self.sequence_number[cmd]
        self.sequence_number[cmd] = (seq + 1) % 100
        result = self.blackboxes[id].send_and_wait(cmd, seq, data)
        parse_fdm_log(result)
        return result

import logging
import queue
import requests
import threading
import time

from collections.abc import Generator
from odoo.addons.iot_drivers.tools import helpers, system
from odoo.addons.iot_drivers.tools.system import IOT_IDENTIFIER
from odoo.netsvc import ColoredFormatter

_logger = logging.getLogger(__name__)


@helpers.require_db
class ServerLogger(logging.Handler):
    _previous_disconnection: float = 0.0
    _MAX_QUEUE_SIZE: int = 1000

    def __init__(self, server_url=None):
        """Custom logging handler which send IoT logs using asynchronous requests.
        To avoid spamming the server, we send logs by batch each X seconds

        :param str server_url: URL of the Odoo server (provided by decorator).
        """
        super().__init__()
        self.setFormatter(
            ColoredFormatter('%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: %(message)s %(perf_info)s')
        )
        self.addFilter(self._logs_filter)
        self._server_iot_log_url = server_url + '/iot/log'
        self._db_name = system.get_conf('db_name') or ''
        self._queue = queue.Queue(self._MAX_QUEUE_SIZE)
        self._active = True
        self._flush_thread = threading.Thread(target=self.share_logs_loop, name="ThreadServerLogger", daemon=True)
        self._flush_thread.start()

    def share_logs_loop(self):
        while self._active:  # allow to exit the loop on thread.join
            time.sleep(0.5)  # sleep before sending logs
            self._share_logs()

    def get_batch(self) -> Generator[bytes]:
        """Generate a batch of log records to send to the server.
        The amount of log records is limited to 50 to avoid too heavy requests.
        """
        yield f"identifier {IOT_IDENTIFIER}<log/>\n".encode()
        for _ in range(50):  # max 50 logs per batch
            try:
                log_record = self._queue.get_nowait()
                yield self.format_logs(log_record.levelno, self.format(log_record))
            except queue.Empty:
                break

        # Report to the server if the queue is close from saturation
        queue_size = self._queue.qsize()
        if queue_size >= .8 * self._MAX_QUEUE_SIZE:
            log_message = f"The Server Logger queue is {100 * queue_size / self._MAX_QUEUE_SIZE:.2f}%"
            _logger.warning(log_message)  # As we don't log our own logs, this will be part of the IoT logs
            # In order to report this to the server (on the current batch) we will append it manually
            yield self.format_logs(logging.WARNING, log_message)

    def _share_logs(self):
        odoo_session = requests.Session()
        odoo_session.headers = {
            'X-Odoo-Database': self._db_name,
            'User-Agent': 'OdooIoTBox/1.0',
        }
        if self._queue.qsize() == 0:
            return
        try:
            odoo_session.post(
                self._server_iot_log_url,
                data=self.get_batch(),
                timeout=10
            ).raise_for_status()
            self._previous_disconnection = 0.0
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            now = time.time()
            if now > self._previous_disconnection + 5 * 60:  # 5 minutes
                _logger.info("Failed to send logs to the db. It is likely down: %s", e)
                self._previous_disconnection = now
        except Exception:  # noqa: BLE001
            _logger.exception('Unexpected error happened while sending logs to server')

    def emit(self, record: logging.LogRecord) -> None:
        """This is important that this method is as fast as possible.
        The log calls will be waiting for this function to finish
        """
        if not self._active:
            return
        try:  # noqa: SIM105
            self._queue.put_nowait(record)
        except queue.Full:
            pass

    def close(self):
        self._active = False
        self._flush_thread and self._flush_thread.join()  # let a last flush
        super().close()

    @staticmethod
    def format_logs(log_level: int, log_message: str) -> bytes:
        """Format log message to be sent to the server.

        :param log_level: Logging level of the message.
        :param log_message: The log message.
        :return: Formatted log message.
        """
        return f"{log_level},{log_message}<log/>\n".encode()

    @staticmethod
    def _logs_filter(log_record):
        return (
                log_record.name != __name__
                and not (
                    log_record.name == "werkzeug"
                    and log_record.args
                    and len(log_record.args) > 0
                    and str(log_record.args[0]).startswith('GET /hw_proxy/hello ')
            )
        )


server_logger = ServerLogger()
if server_logger:
    # Set it in the 'root' logger, on which every logger (including odoo) is a child
    logging.getLogger().addHandler(server_logger)

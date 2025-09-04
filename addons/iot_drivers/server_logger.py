import logging
import queue
import requests
import threading
import time

from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.tools.system import IS_TEST
from odoo.netsvc import ColoredFormatter

_logger = logging.getLogger(__name__)

IOT_LOG_TO_SERVER_CONFIG_NAME = 'iot_log_to_server'  # config name in odoo.conf


class AsyncHTTPHandler(logging.Handler):
    """
    Custom logging handler which send IoT logs using asynchronous requests.
    To avoid spamming the server, we send logs by batch each X seconds
    """
    _MAX_QUEUE_SIZE = 1000
    """Maximum queue size. If a log record is received but the queue if full it will be discarded"""
    _MAX_BATCH_SIZE = 50
    """Maximum number of sent logs batched at once. Used to avoid too heavy request. Log records still in the queue will
    be handle in future flushes"""
    _FLUSH_INTERVAL = 0.5
    """How much seconds it will sleep before checking for new logs to send"""
    _REQUEST_TIMEOUT = 0.5
    """Amount of seconds to wait per log to send before timeout"""
    _DELAY_BEFORE_NO_SERVER_LOG = 5 * 60  # 5 minutes
    """Minimum delay in seconds before we log a server disconnection.
    Used in order to avoid the IoT log file to have a log recorded each _FLUSH_INTERVAL (as this value is very small)"""

    def __init__(self, odoo_server_url, active):
        """
        :param odoo_server_url: Odoo Server URL
        """
        super().__init__()
        self._odoo_server_url = odoo_server_url
        self._db_name = helpers.get_conf('db_name') or ''
        self._log_queue = queue.Queue(self._MAX_QUEUE_SIZE)
        self._flush_thread = None
        self._active = None
        self._next_disconnection_time = None
        self.toggle_active(active)

    def toggle_active(self, is_active):
        """
        Switch it on or off the handler (depending on the IoT setting) without the need to close/reset it
        """
        self._active = is_active
        if self._active and self._odoo_server_url:
            # Start the thread to periodically flush logs
            self._flush_thread = threading.Thread(target=self._periodic_flush, name="ThreadServerLogSender", daemon=True)
            self._flush_thread.start()
        else:
            self._flush_thread and self._flush_thread.join()  # let a last flush

    def _periodic_flush(self):
        odoo_session = requests.Session()
        while self._odoo_server_url and self._active:  # allow to exit the loop on thread.join
            time.sleep(self._FLUSH_INTERVAL)
            self._flush_logs(odoo_session)

    def _flush_logs(self, odoo_session):
        def convert_to_byte(s):
            return bytes(s, encoding="utf-8") + b'<log/>\n'

        def convert_server_line(log_level, line_formatted):
            return convert_to_byte(f"{log_level},{line_formatted}")

        def empty_queue():
            yield convert_to_byte(f"identifier {helpers.get_identifier()}")
            for _ in range(self._MAX_BATCH_SIZE):
                # Use a limit to avoid having too heavy requests & infinite loop of the queue receiving new entries
                try:
                    log_record = self._log_queue.get_nowait()
                    yield convert_server_line(log_record.levelno, self.format(log_record))
                except queue.Empty:
                    break

            # Report to the server if the queue is close from saturation
            if queue_size >= .8 * self._MAX_QUEUE_SIZE:
                log_message = "The IoT {} queue is saturating: {}/{} ({:.2f}%)".format(  # noqa: UP032
                    self.__class__.__name__, queue_size, self._MAX_QUEUE_SIZE,
                    100 * queue_size / self._MAX_QUEUE_SIZE)
                _logger.warning(log_message)  # As we don't log our own logs, this will be part of the IoT logs
                # In order to report this to the server (on the current batch) we will append it manually
                yield convert_server_line(logging.WARNING, log_message)

        queue_size = self._log_queue.qsize()  # This is an approximate value

        if not self._odoo_server_url or queue_size == 0:
            return
        try:
            odoo_session.post(
                self._odoo_server_url + '/iot/log',
                data=empty_queue(),
                headers={'X-Odoo-Database': self._db_name},
                timeout=self._REQUEST_TIMEOUT
            ).raise_for_status()
            self._next_disconnection_time = None
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as request_errors:
            now = time.time()
            if not self._next_disconnection_time or now >= self._next_disconnection_time:
                _logger.info("Connection with the server to send the logs failed. It is likely down: %s", request_errors)
                self._next_disconnection_time = now + self._DELAY_BEFORE_NO_SERVER_LOG
        except Exception as _:
            _logger.exception('Unexpected error happened while sending logs to server')

    def emit(self, record):
        # This is important that this method is as fast as possible.
        # The log calls will be waiting for this function to finish
        if not self._active:
            return
        try:  # noqa: SIM105
            self._log_queue.put_nowait(record)
        except queue.Full:
            pass

    def close(self):
        self.toggle_active(False)
        super().close()


def close_server_log_sender_handler():
    _server_log_sender_handler.close()


def get_odoo_config_log_to_server_option():
    # Enabled by default if not in test mode
    return not IS_TEST and (helpers.get_conf(IOT_LOG_TO_SERVER_CONFIG_NAME, section='options') or True)


def check_and_update_odoo_config_log_to_server_option(new_state):
    """
    :return: wherever the config file need to be updated or not
    """
    if get_odoo_config_log_to_server_option() != new_state:
        helpers.update_conf({IOT_LOG_TO_SERVER_CONFIG_NAME, new_state}, section='options')
        _server_log_sender_handler.toggle_active(new_state)
        return True
    return False


def _server_log_sender_handler_filter(log_record):
    def _filter_my_logs():
        """Filter out our own logs (to avoid infinite loop)"""
        return log_record.name == __name__

    def _filter_frequent_irrelevant_calls():
        """Filter out this frequent irrelevant HTTP calls, to avoid spamming the server with useless logs"""
        return (
            log_record.name == 'werkzeug'
            and log_record.args
            and len(log_record.args) > 0
            and str(log_record.args[0]).startswith('GET /hw_proxy/hello ')
        )

    return not (_filter_my_logs() or _filter_frequent_irrelevant_calls())


# The server URL is set once at initlialisation as the IoT will always restart if the URL is changed
# The only other possible case is when the server URL value is "Cleared",
# in this case we force close the log handler (as it does not make sense anymore)
_server_log_sender_handler = AsyncHTTPHandler(helpers.get_odoo_server_url(), get_odoo_config_log_to_server_option())
if not IS_TEST:
    _server_log_sender_handler.setFormatter(ColoredFormatter('%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: %(message)s %(perf_info)s'))
    _server_log_sender_handler.addFilter(_server_log_sender_handler_filter)
    # Set it in the 'root' logger, on which every logger (including odoo) is a child
    logging.getLogger().addHandler(_server_log_sender_handler)

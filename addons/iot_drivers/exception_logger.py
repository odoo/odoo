
from io import StringIO

import logging
import sys

from odoo.addons.iot_drivers.tools.system import IS_TEST

_logger = logging.getLogger(__name__)


class ExceptionLogger:
    """
    Redirect any unhandled python exception to the logger to keep track of them in the log file.
    """
    def __init__(self):
        self._buffer = StringIO()

    def write(self, message):
        self._buffer.write(message)
        if message.endswith('\n'):
            self._flush_buffer()

    def _flush_buffer(self):
        self._buffer.seek(0)
        _logger.error(self._buffer.getvalue().rstrip('\n'))
        self._buffer = StringIO()  # Reset the buffer

    def flush(self):
        if self._buffer.tell() > 0:
            self._flush_buffer()

    def close(self):
        self.flush()


if not IS_TEST:
    sys.stderr = ExceptionLogger()

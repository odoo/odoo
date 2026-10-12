"""Redirect any unhandled python exception to the logger
to keep track of them in the log file.
"""
import logging
import sys
import threading

from odoo.addons.iot_drivers.tools.system import IS_TEST

_logger = logging.getLogger(__name__)


def _log_exception(args):
    _logger.error(
        "Unhandled exception",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _log_thread_exception(args):
    _logger.error(
        "Unhandled exception in thread %s",
        args.thread.name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


if not IS_TEST:
    sys.excepthook = _log_exception
    threading.excepthook = _log_thread_exception

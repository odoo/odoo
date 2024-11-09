
import logging
from threading import current_thread, Lock
from typing import Dict, Set

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class LogFilterDebugDB(logging.Filter):
    def __init__(self):
        super().__init__('LogFilterDebugDB')
        self._logger_db: Dict[str, Set[str]] = {}
        """A mapping of debug loggers to the databases they are enabled for.
        e.g. {'odoo.addons.logger_debug': {'db1', 'db2'}}"""
        self._logger_lock = Lock()

    def filter(self, record):
        if record.levelno != logging.DEBUG or (ct_db := getattr(current_thread(), 'dbname', None)) is None:
            return True
        # TODO: Check how to handle the cases like IoT logs logger which have a debug level
        return (logger_dbs := self._logger_db.get(record.name)) and ct_db in logger_dbs

    def add_logger(self, logger_name: str):
        """Add a logger to the debug loggers for the current database."""
        if not (ct_db:= getattr(current_thread(), 'dbname', None)):
            raise UserError("No database is currently set")

        with self._logger_lock:
            logger = logging.getLogger(logger_name)
            if logger_name not in self._logger_db:
                if logger.getEffectiveLevel() == logging.DEBUG:
                    raise UserError(f"Logger {logger_name} is already set to DEBUG")
                logger.setLevel(logging.DEBUG)
                logger.addFilter(self)
                self._logger_db[logger_name] = set()
            self._logger_db[logger_name].add(ct_db)

        _logger.info("Added logger %s to debug loggers for db %s", logger_name, ct_db)


log_filter_debug_db = None

def get_log_filter_debug_db() -> LogFilterDebugDB:
    global log_filter_debug_db  # TODO: Check if this is the right way to do it
    if log_filter_debug_db is None:
        log_filter_debug_db = LogFilterDebugDB()
    return log_filter_debug_db

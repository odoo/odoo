import contextlib
import json
import logging
import threading

from odoo import tools, sql_db

__all__ = [  # noqa: RUF022
    "ColoredFormatter",
    "PostgreSQLHandler",
    'BLACK', 'RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE', 'HIGH_INTENSITY', 'DEFAULT',
    'HI_BLACK', 'HI_RED', 'HI_GREEN', 'HI_YELLOW', 'HI_BLUE', 'HI_MAGENTA', 'HI_CYAN', 'HI_WHITE',
    "RESET_SEQ", "COLOR_SEQ", "BOLD_SEQ", "COLOR_PATTERN", "TRUE_COLOR_PATTERN",
    "LEVEL_COLOR_MAPPING", "PID_COLORS",
]


class PostgreSQLHandler(logging.Handler):
    """ PostgreSQL Logging Handler will store logs in the database, by default
    the current database, can be set using --log-db=DBNAME
    """

    def __init__(self, log_db):
        super().__init__()
        self._support_metadata = False
        if log_db == '%d':
            self._log_db = None
        else:
            self._log_db = log_db
            with contextlib.suppress(Exception), tools.mute_logger('odoo.sql_db'), sql_db.db_connect(self._log_db, allow_uri=True).cursor() as cr:
                cr.execute("""SELECT 1 FROM information_schema.columns WHERE table_name='ir_logging' and column_name='metadata' AND table_schema = current_schema""")
                self._support_metadata = bool(cr.fetchone())

    def emit(self, record):
        ct = threading.current_thread()
        ct_db = getattr(ct, 'dbname', None)
        dbname = self._log_db or ct_db
        if not dbname:
            return
        with contextlib.suppress(Exception), tools.mute_logger('odoo.sql_db'), sql_db.db_connect(dbname, allow_uri=True).cursor() as cr:
            # preclude risks of deadlocks
            cr.execute("SET LOCAL statement_timeout = 1000")
            msg = str(record.msg)
            if record.args:
                msg = msg % record.args
            traceback = getattr(record, 'exc_text', '')
            if traceback:
                msg = f"{msg}\n{traceback}"
            # we do not use record.levelname because it may have been changed by ColoredFormatter.
            levelname = logging.getLevelName(record.levelno)

            val = ('server', ct_db, record.name, levelname, msg, record.pathname, record.lineno, record.funcName)

            if self._support_metadata and record.test:
                cr.execute("""
                    INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func, metadata)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (*val, json.dumps({'test': record.test})))
                return

            cr.execute("""
                INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s)
            """, val)


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, HIGH_INTENSITY, DEFAULT = range(10)
HI_BLACK, HI_RED, HI_GREEN, HI_YELLOW, HI_BLUE, HI_MAGENTA, HI_CYAN, HI_WHITE = range(
    BLACK + HIGH_INTENSITY, WHITE + HIGH_INTENSITY + 1)
# The background is set with 40 plus the number of the color, and the foreground with 30
# These are the sequences needed to get colored output
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"
COLOR_PATTERN = f"{COLOR_SEQ}{COLOR_SEQ}%s{RESET_SEQ}"
TRUE_COLOR_PATTERN = f"\033[38;5;%dm%s{RESET_SEQ}"
LEVEL_COLOR_MAPPING = {
    logging.DEBUG: (BLUE, DEFAULT),
    logging.INFO: (GREEN, DEFAULT),
    logging.WARNING: (YELLOW, DEFAULT),
    logging.ERROR: (RED, DEFAULT),
    logging.CRITICAL: (WHITE, RED),
}
# all colors but black, grey, silver, WARNING and ERROR; length must be prime.
PID_COLORS = (
    GREEN, BLUE, MAGENTA, CYAN,
    HI_RED, HI_GREEN, HI_YELLOW, HI_BLUE, HI_MAGENTA, HI_CYAN, HI_WHITE,
)


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        fg_color, bg_color = LEVEL_COLOR_MAPPING.get(record.levelno, (GREEN, DEFAULT))
        if tools.config.colors['loglevel']:
            record.levelname = COLOR_PATTERN % (30 + fg_color, 40 + bg_color, record.levelname)
        if tools.config.colors['pid']:
            record.process = TRUE_COLOR_PATTERN % (PID_COLORS[record.thread_native % len(PID_COLORS)], record.thread_native)
        return super().format(record)

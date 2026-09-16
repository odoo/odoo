import contextlib
import json
import logging
import logging.config
import logging.handlers
import os
import platform
import sys
import traceback
import warnings
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol, TextIO, cast

from . import db, release, tools
from .db.replica import is_readonly_cursor_enabled
from .db.schema import column_exists
from .libs.colors import BLUE, DEFAULT, GREEN, RED, WHITE, YELLOW, colorize
from .libs.json import dumps as json_dumps
from .libs.worker_thread import current_worker_thread

if TYPE_CHECKING:
    import types

_logger = logging.getLogger(__name__)


class WatchedFileHandler(logging.handlers.WatchedFileHandler):
    def __init__(self, filename: str) -> None:
        self.errors = None
        super().__init__(filename)
        self._builtin_open = None

    def _open(self) -> TextIOWrapper:
        return cast(
            "TextIOWrapper",
            Path(self.baseFilename).open(
                self.mode, encoding=self.encoding, errors=self.errors
            ),
        )


class PostgreSQLHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._support_metadata: bool = False
        if tools.config["log_db"] != "%d":
            with (
                contextlib.suppress(Exception),
                tools.mute_logger("odoo.db"),
                db.db_connect(tools.config["log_db"], allow_uri=True).cursor() as cr,
            ):
                self._support_metadata = bool(
                    column_exists(cr, "ir_logging", "metadata")
                )

    def emit(self, record: logging.LogRecord) -> None:
        ct_db = getattr(current_worker_thread(), "dbname", None)
        dbname = (
            tools.config["log_db"]
            if tools.config["log_db"] and tools.config["log_db"] != "%d"
            else ct_db
        )
        if not dbname:
            return
        with (
            contextlib.suppress(Exception),
            tools.mute_logger("odoo.db"),
            db.db_connect(dbname, allow_uri=True).cursor() as cr,
        ):
            cr.execute("SET LOCAL statement_timeout = 1000")
            msg = str(record.msg)
            if record.args:
                msg %= record.args
            traceback = getattr(record, "exc_text", "")
            if traceback:
                msg = f"{msg}\n{traceback}"
            levelname = logging.getLevelName(record.levelno)

            val = (
                "server",
                ct_db,
                record.name,
                levelname,
                msg,
                record.pathname,
                record.lineno,
                record.funcName,
            )

            if self._support_metadata:
                from . import modules

                metadata = {}
                test = modules.module.current_test
                if test is not True and test:
                    with contextlib.suppress(Exception):
                        metadata["test"] = test.get_log_metadata()

                if metadata:
                    cr.execute(
                        """
                        INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func, metadata)
                        VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (*val, json_dumps(metadata)),
                    )
                    return

            cr.execute(
                """
                INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                val,
            )


LEVEL_COLOR_MAPPING: Final[dict[int, tuple[int, int]]] = {
    logging.DEBUG: (BLUE, DEFAULT),
    logging.INFO: (GREEN, DEFAULT),
    logging.WARNING: (YELLOW, DEFAULT),
    logging.ERROR: (RED, DEFAULT),
    logging.CRITICAL: (WHITE, RED),
}


class PerfFilter(logging.Filter):
    def format_perf(
        self, query_count: int, query_time: float, remaining_time: float
    ) -> tuple[str, str, str]:
        return (
            f"{query_count:d}",
            f"{query_time:.3f}",
            f"{remaining_time:.3f}",
        )

    def format_cursor_mode(self, cursor_mode: str | None) -> str:
        return cursor_mode or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        perf_record = cast("LogRecord", record)
        worker = current_worker_thread()
        if hasattr(worker, "query_count"):
            query_count = worker.query_count
            query_time = worker.query_time
            perf_t0 = worker.perf_t0
            remaining_time = tools.real_time() - perf_t0 - query_time
            perf_record.perf_info = "%s %s %s" % self.format_perf(
                query_count, query_time, remaining_time
            )
            if is_readonly_cursor_enabled():
                cursor_mode = worker.cursor_mode
                perf_record.perf_info = (
                    f"{perf_record.perf_info} {self.format_cursor_mode(cursor_mode)}"
                )
            del worker.query_count
        elif is_readonly_cursor_enabled():
            perf_record.perf_info = "- - - -"
        else:
            perf_record.perf_info = "- - -"
        return True


class ColoredPerfFilter(PerfFilter):
    def format_perf(
        self, query_count: int, query_time: float, remaining_time: float
    ) -> tuple[str, str, str]:
        def colorize_time(time, format, low=1, high=5):
            if time > high:
                return colorize(format % time, RED)
            if time > low:
                return colorize(format % time, YELLOW)
            return format % time

        return (
            colorize_time(query_count, "%d", 100, 1000),
            colorize_time(query_time, "%.3f", 0.1, 3),
            colorize_time(remaining_time, "%.3f", 1, 5),
        )

    def format_cursor_mode(self, cursor_mode: str | None) -> str:
        cursor_mode = super().format_cursor_mode(cursor_mode)
        cursor_mode_color = (
            RED if cursor_mode == "ro->rw" else YELLOW if cursor_mode == "rw" else GREEN
        )
        return colorize(cursor_mode, cursor_mode_color)


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fg_color, bg_color = LEVEL_COLOR_MAPPING.get(record.levelno, (GREEN, DEFAULT))
        record.levelname = colorize(record.levelname, fg_color, bg_color)
        return super().format(record)


def root_handler_uses_colors() -> bool:
    handlers = logging.getLogger().handlers
    return bool(handlers) and isinstance(handlers[0].formatter, ColoredFormatter)


class JSONFormatter(logging.Formatter):
    def __init__(
        self, *args, record_keys=None, ignore_record_keys=None, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.record_keys = record_keys
        if ignore_record_keys is not None:
            self.ignore_record_keys = set(ignore_record_keys)
        else:
            self.ignore_record_keys = {
                "msecs",
                "relativeCreated",
                "asctime",
                "filename",
                "module",
                "msg",
                "args",
            }

    def format(self, record: logging.LogRecord) -> str:
        record_json: dict[str, object] = {}
        record_keys = self.record_keys
        if record_keys is None:
            record_keys = self._get_record_keys_default(record)
        for key in record_keys:
            if key == "exc_info":
                if record.exc_info:
                    if not record.exc_text:
                        record.exc_text = self.formatException(record.exc_info)
                    record_json[key] = record.exc_text
            elif key == "stack_info":
                if record.stack_info:
                    record_json[key] = self.formatStack(record.stack_info)
            elif key == "message":
                record.message = record.getMessage()
                record_json[key] = record.message
            elif key == "asctime":
                record.asctime = self.formatTime(record, self.datefmt)
                record_json[key] = record.asctime
            elif key == "test":
                from .modules import module

                test = module.current_test
                if test is not True and test:
                    with contextlib.suppress(Exception):
                        record_json[key] = test.get_log_metadata()
            else:
                value = getattr(record, key, None)
                if value is not None:
                    record_json[key] = value

        return json.dumps(record_json, default=str)

    def _get_record_keys_default(self, record: logging.LogRecord) -> list:
        return sorted(
            (record.__dict__.keys() | {"message", "test"}) - self.ignore_record_keys
        )


class LogRecord(logging.LogRecord):
    def __init__(
        self,
        name: str,
        level: int,
        pathname: str,
        lineno: int,
        msg: object,
        args: tuple | dict[str, object] | None,
        exc_info: tuple[type[BaseException], BaseException, types.TracebackType | None]
        | tuple[None, None, None]
        | None,
        func: str | None = None,
        sinfo: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            name,
            level,
            pathname,
            lineno,
            msg,
            args,
            exc_info,
            func=func,
            sinfo=sinfo,
            **kwargs,
        )
        self.perf_info = ""
        self.pid = os.getpid()
        worker = current_worker_thread()
        self.dbname = getattr(worker, "dbname", "?")
        uid = getattr(worker, "uid", None)
        self.uid = uid if uid is not None else "-"
        self.request_id = getattr(worker, "request_id", "-")


class _ShowWarning(Protocol):
    def __call__(
        self,
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: TextIO | None = None,
        line: str | None = None,
    ) -> None: ...


showwarning: _ShowWarning = warnings.showwarning


def _silence_dependency_warnings() -> None:
    warnings.simplefilter("default", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore",
        r"^\'urllib3.contrib.pyopenssl\' module is deprecated.+",
        category=DeprecationWarning,
    )
    for module in [
        "babel.util",
        "zeep.loader",
        "ofxparse",
        "astroid",
        "requests_toolbelt",
    ]:
        warnings.filterwarnings("ignore", category=DeprecationWarning, module=module)

    warnings.filterwarnings(
        "ignore",
        r"^PyUnicode_FromUnicode\(NULL, size\) is deprecated",
        category=DeprecationWarning,
    )
    warnings.filterwarnings("ignore", category=BytesWarning, module="odoo.tools.image")

    warnings.filterwarnings(
        "ignore",
        r"^datetime.datetime.utcnow\(\) is deprecated and scheduled for removal in a future version.*",
        category=DeprecationWarning,
    )

    warnings.filterwarnings(
        "ignore",
        r"pkg_resources is deprecated as an API.+",
        category=DeprecationWarning,
    )
    warnings.filterwarnings(
        "ignore",
        r"Deprecated call to \`pkg_resources.declare_namespace.+",
        category=DeprecationWarning,
    )

    warnings.filterwarnings(
        "ignore",
        r"invalid escape sequence",
        category=DeprecationWarning,
        module=".*vobject",
    )
    warnings.filterwarnings(
        "ignore",
        r"invalid escape sequence",
        category=SyntaxWarning,
        module=".*vobject",
    )


def _apply_log_config_file() -> dict | None:
    log_config = tools.config["log_config"]
    if not log_config:
        return None
    with Path(log_config).open("rb") as fobj:
        conf = json.load(fobj)
        conf["disable_existing_loggers"] = False
    logging.config.dictConfig(conf)
    return conf


def _install_log_handler() -> None:
    format = "%(asctime)s %(pid)s %(levelname)s uid:%(uid)s %(dbname)s rid:%(request_id)s %(name)s: %(message)s %(perf_info)s"
    handler: logging.Handler = logging.StreamHandler()

    if tools.config["syslog"]:
        if os.name == "nt":
            handler = logging.handlers.NTEventLogHandler(
                f"{release.description} {release.version}"
            )
        elif platform.system() == "Darwin":
            handler = logging.handlers.SysLogHandler("/var/run/log")
        else:
            handler = logging.handlers.SysLogHandler("/dev/log")
        format = f"{release.description} {release.version}:%(dbname)s:%(levelname)s:%(name)s:%(message)s"

    elif tools.config["logfile"]:
        logf = tools.config["logfile"]
        try:
            logpath = Path(logf)
            logpath.parent.mkdir(parents=True, exist_ok=True)
            if os.name == "posix":
                handler = WatchedFileHandler(logf)
            else:
                handler = logging.FileHandler(logf)
        except Exception:
            sys.stderr.write(
                "ERROR: couldn't create the logfile directory. Logging to the standard output.\n"
            )

    def is_a_tty(stream):
        return hasattr(stream, "fileno") and os.isatty(stream.fileno())

    if (
        os.name == "posix"
        and isinstance(handler, logging.StreamHandler)
        and (is_a_tty(handler.stream) or os.environ.get("ODOO_PY_COLORS"))
    ):
        formatter: logging.Formatter = ColoredFormatter(format)
        perf_filter: PerfFilter = ColoredPerfFilter()
    else:
        formatter = logging.Formatter(format)
        perf_filter = PerfFilter()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger(ACCESS_LOGGER).addFilter(perf_filter)

    if tools.config["log_db"]:
        db_levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        postgresqlHandler = PostgreSQLHandler()
        postgresqlHandler.setLevel(
            int(
                db_levels.get(
                    tools.config["log_db_level"], tools.config["log_db_level"]
                )
            )
        )
        logging.getLogger().addHandler(postgresqlHandler)


def _apply_configured_levels() -> None:
    pseudo_config = PSEUDOCONFIG_MAPPER.get(tools.config["log_level"], [])

    logconfig = tools.config["log_handler"]

    logging_configurations = DEFAULT_LOG_CONFIGURATION + pseudo_config + logconfig
    if any(item.strip().startswith("werkzeug:") for item in logconfig):
        _logger.warning(
            "log_handler names werkzeug, which no longer carries the HTTP access log;"
            " set %s instead",
            ACCESS_LOGGER,
        )
    for logconfig_item in logging_configurations:
        loggername, level = logconfig_item.strip().split(":")
        level = getattr(logging, level, logging.INFO)
        logger = logging.getLogger(loggername)
        logger.setLevel(level)

    for logconfig_item in logging_configurations:
        _logger.debug('logger level set: "%s"', logconfig_item)


def init_logger() -> None:
    global showwarning  # noqa: PLW0603  saves the stdlib hook we replace, once per process
    if logging.getLogRecordFactory() is LogRecord:
        return

    logging.setLogRecordFactory(LogRecord)

    logging.captureWarnings(True)
    showwarning = warnings.showwarning
    warnings.showwarning = showwarning_with_traceback

    _silence_dependency_warnings()
    from .tools.translate import resetlocale

    resetlocale()

    conf = _apply_log_config_file()
    if conf is not None and not conf.get("keep_odoo_default", False):
        return
    _install_log_handler()
    _apply_configured_levels()


ACCESS_LOGGER: Final[str] = "odoo.service.http.access"
# The access logger sits under "odoo" but keeps werkzeug's standing: INFO unless a
# preset or log_handler names it, so --log-level=debug does not print every static
# request.
DEFAULT_LOG_CONFIGURATION: Final[list[str]] = [
    f"{ACCESS_LOGGER}:INFO",
    "odoo.http.rpc.request:INFO",
    "odoo.http.rpc.response:INFO",
    "fontTools:WARNING",
    ":INFO",
]
PSEUDOCONFIG_MAPPER: Final[dict[str, list[str]]] = {
    "debug_rpc_answer": ["odoo:DEBUG", "odoo.db:INFO", "odoo.http.rpc:DEBUG"],
    "debug_rpc": ["odoo:DEBUG", "odoo.db:INFO", "odoo.http.rpc.request:DEBUG"],
    "debug": ["odoo:DEBUG", "odoo.db:INFO"],
    "debug_sql": ["odoo.db:DEBUG"],
    "info": [],
    "runbot": ["odoo:RUNBOT", f"{ACCESS_LOGGER}:WARNING", "werkzeug:WARNING"],
    "warn": ["odoo:WARNING", f"{ACCESS_LOGGER}:WARNING", "werkzeug:WARNING"],
    "error": ["odoo:ERROR", f"{ACCESS_LOGGER}:ERROR", "werkzeug:ERROR"],
    "critical": ["odoo:CRITICAL", f"{ACCESS_LOGGER}:CRITICAL", "werkzeug:CRITICAL"],
}

RUNBOT: Final[int] = 25

logging.RUNBOT = RUNBOT  # type: ignore[attr-defined]
logging.addLevelName(RUNBOT, "INFO")
logging._nameToLevel["INFO"] = logging.INFO
IGNORE: Final[frozenset[str]] = frozenset(
    {
        "Comparison between bytes and int",
    }
)


def showwarning_with_traceback(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    if (
        category is BytesWarning
        and isinstance(message, Warning)
        and message.args[0] in IGNORE
    ):
        return None

    filtered: list[traceback.FrameSummary] = []
    for frame in traceback.extract_stack():
        if frame.name == "__call__" and frame.filename.endswith(
            "/odoo/http/application.py"
        ):
            filtered.clear()
        if "importlib" not in frame.filename:
            filtered.append(frame)
        if frame.filename == filename and frame.lineno == lineno:
            break
    return showwarning(
        message,
        category,
        filename,
        lineno,
        file=file,
        line="".join(traceback.format_list(filtered)),
    )


def runbot(self: logging.Logger, message: str, *args: object, **kws: Any) -> None:
    self.log(RUNBOT, message, *args, **kws)


logging.Logger.runbot = runbot  # type: ignore[attr-defined]

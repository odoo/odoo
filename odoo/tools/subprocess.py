"""
Subprocess and system process utilities for Odoo.

This module provides utilities for:
- Finding executables in PATH
- PostgreSQL tool discovery and environment setup
- Process debugging (stack traces)
- Command-line argument handling
"""

import logging
import os
import sys
import threading
import traceback
from itertools import groupby as itergroupby

from odoo.libs.filesystem.which import which

from .config import config

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Path utilities
# ----------------------------------------------------------


def find_in_path(name):
    """Find an executable in the system PATH.

    Searches the system PATH environment variable and the configured
    `bin_path` option for the given executable name.

    :param str name: Name of the executable to find
    :return: Full path to the executable, or None if not found
    :rtype: str or None
    """
    path = os.environ.get("PATH", os.defpath).split(os.pathsep)
    if config.get("bin_path") and config["bin_path"] != "None":
        path.append(config["bin_path"])
    return which(name, path=os.pathsep.join(path))


# ----------------------------------------------------------
# PostgreSQL subprocess utilities
# ----------------------------------------------------------


def find_pg_tool(name):
    """Find a PostgreSQL command-line tool.

    Searches for PostgreSQL tools (pg_dump, pg_restore, etc.) using
    the configured `pg_path` option or the system PATH.

    :param str name: Name of the PostgreSQL tool (e.g., 'pg_dump')
    :return: Full path to the tool
    :rtype: str
    :raises Exception: If the tool is not found
    """
    path = None
    if config["pg_path"] and config["pg_path"] != "None":
        path = config["pg_path"]
    try:
        return which(name, path=path)
    except OSError:
        raise Exception(f"Command `{name}` not found.")


def exec_pg_environ():
    """Get environment variables for PostgreSQL subprocess execution.

    Creates a copy of the current environment with PostgreSQL-specific
    variables set according to the Odoo configuration. This is used
    for running pg_dump, pg_restore, and other PostgreSQL tools.

    Note: On systems where pg_restore/pg_dump require an explicit password
    (i.e. on Windows where TCP sockets are used), it is necessary to pass the
    postgres user password in the PGPASSWORD environment variable or in a
    special .pgpass file.

    See also https://www.postgresql.org/docs/current/libpq-envars.html

    :return: Environment dict with PostgreSQL variables set
    :rtype: dict
    """
    env = os.environ.copy()
    if config["db_host"]:
        env["PGHOST"] = config["db_host"]
    if config["db_port"]:
        env["PGPORT"] = str(config["db_port"])
    if config["db_user"]:
        env["PGUSER"] = config["db_user"]
    if config["db_password"]:
        env["PGPASSWORD"] = config["db_password"]
    if config["db_app_name"]:
        env["PGAPPNAME"] = config["db_app_name"].replace("{pid}", f"env{os.getpid()}")[
            :63
        ]
    if config["db_sslmode"]:
        env["PGSSLMODE"] = config["db_sslmode"]
    return env


# ----------------------------------------------------------
# Command-line argument utilities
# ----------------------------------------------------------


def stripped_sys_argv(*strip_args):
    """Return sys.argv with specified arguments stripped.

    Creates a filtered copy of sys.argv suitable for re-execution
    or subprocess spawning, removing arguments that should not be
    passed through (like -s/--save, -u/--update, etc.).

    :param strip_args: Additional argument flags to strip
    :return: Filtered argument list
    :rtype: list[str]
    """
    strip_args = sorted(
        set(strip_args)
        | {
                "-s",
                "--save",
                "-u",
                "--update",
                "-i",
                "--init",
                "--i18n-overwrite",
            }
    )
    assert all(config.parser.has_option(s) for s in strip_args)
    takes_value = {
        s: config.parser.get_option(s).takes_value() for s in strip_args
    }

    longs, shorts = [
        tuple(y) for _, y in itergroupby(strip_args, lambda x: x.startswith("--"))
    ]
    longs_eq = tuple(l + "=" for l in longs if takes_value[l])

    args = sys.argv[:]

    def strip(args, i):
        return (
            args[i].startswith(shorts)
            or args[i].startswith(longs_eq)
            or (args[i] in longs)
            or (i >= 1 and (args[i - 1] in strip_args) and takes_value[args[i - 1]])
        )

    return [x for i, x in enumerate(args) if not strip(args, i)]


# ----------------------------------------------------------
# Debugging utilities
# ----------------------------------------------------------

# ensure we have a non patched time for query times when using freezegun
import time

real_time = time.time.__call__  # type: ignore


def dumpstacks(sig=None, frame=None, thread_idents=None, log_level=logging.INFO):
    """Dump stack traces for running threads and greenlets.

    Signal handler that logs stack traces for debugging purposes.
    Useful for diagnosing hangs or understanding thread state.

    :param sig: Signal number (when used as signal handler)
    :param frame: Current stack frame (when used as signal handler)
    :param thread_idents: Optional sequence of thread IDs to dump
        (if None, dumps all threads)
    :param log_level: Logging level for output (default: INFO)
    """
    code = []

    def extract_stack(stack):
        for filename, lineno, name, line in traceback.extract_stack(stack):
            yield f'File: "{filename}", line {lineno}, in {name}'
            if line:
                yield f"  {line.strip()}"

    # code from http://stackoverflow.com/questions/132058/getting-stack-trace-from-a-running-python-application#answer-2569696
    # modified for python 2.5 compatibility
    threads_info = {
        th.ident: {
            "repr": repr(th),
            "uid": getattr(th, "uid", "n/a"),
            "dbname": getattr(th, "dbname", "n/a"),
            "url": getattr(th, "url", "n/a"),
            "query_count": getattr(th, "query_count", "n/a"),
            "query_time": getattr(th, "query_time", None),
            "perf_t0": getattr(th, "perf_t0", None),
        }
        for th in threading.enumerate()
    }
    for threadId, stack in sys._current_frames().items():
        if not thread_idents or threadId in thread_idents:
            thread_info = threads_info.get(threadId, {})
            query_time = thread_info.get("query_time")
            perf_t0 = thread_info.get("perf_t0")
            remaining_time = None
            if query_time is not None and perf_t0:
                remaining_time = f"{real_time() - perf_t0 - query_time:.3f}"
                query_time = f"{query_time:.3f}"
            # qc:query_count qt:query_time pt:python_time (aka remaining time)
            repr_ = thread_info.get("repr", threadId)
            dbname = thread_info.get("dbname", "n/a")
            uid = thread_info.get("uid", "n/a")
            url = thread_info.get("url", "n/a")
            qc = thread_info.get("query_count", "n/a")
            qt = query_time or "n/a"
            pt = remaining_time or "n/a"
            code.append(
                f"\n# Thread: {repr_} (db:{dbname}) (uid:{uid}) (url:{url}) (qc:{qc} qt:{qt} pt:{pt})"
            )
            for line in extract_stack(stack):
                code.append(line)

    _logger.log(log_level, "\n".join(code))

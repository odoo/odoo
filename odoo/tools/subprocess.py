import logging
import os
import shutil
import sys
import threading
import traceback
from typing import Any

from odoo.libs.datetime import real_time
from odoo.libs.debug_log import DebugLog

from .config import config

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def get_executable_path(name: str) -> str:
    path = os.environ.get("PATH", os.defpath).split(os.pathsep)
    if config["bin_path"]:
        path.append(config["bin_path"])
    executable = shutil.which(name, path=os.pathsep.join(path))
    _debug.logic(
        "subprocess.executable_resolved",
        name=name,
        path=executable,
        bin_path=config["bin_path"] or None,
    )
    if executable is None:
        raise FileNotFoundError(f"Command `{name}` not found.")
    return executable


def get_pg_tool_path(name: str) -> str:
    path = config["pg_path"] or None
    executable = shutil.which(name, path=path)
    if executable is None:
        _debug.logic("subprocess.pg_tool_missing", name=name, pg_path=path)
        raise FileNotFoundError(f"Command `{name}` not found.")
    _debug.logic("subprocess.pg_tool_resolved", name=name, path=executable)
    return executable


def exec_pg_environ() -> dict[str, str]:
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
    _debug.logic(
        "subprocess.pg_environ",
        keys=sorted(key for key in env if key.startswith("PG") and key != "PGPASSWORD"),
        password=bool(config["db_password"]),
    )
    return env


def stripped_sys_argv(*strip_args: str) -> list[str]:
    stripped = sorted(
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
    unknown = [s for s in stripped if not config.parser.has_option(s)]
    if unknown:
        msg = f"Unknown option(s) to strip: {', '.join(unknown)}"
        raise ValueError(msg)
    takes_value = {
        s: opt.takes_value()
        for s in stripped
        if (opt := config.parser.get_option(s)) is not None
    }

    longs = tuple(a for a in stripped if a.startswith("--"))
    shorts = tuple(a for a in stripped if not a.startswith("--"))
    longs_eq = tuple(l + "=" for l in longs if takes_value[l])

    args = sys.argv[:]

    def strip(args, i):
        return (
            args[i].startswith(shorts)
            or args[i].startswith(longs_eq)
            or (args[i] in longs)
            or (i >= 1 and (args[i - 1] in stripped) and takes_value[args[i - 1]])
        )

    kept = [x for i, x in enumerate(args) if not strip(args, i)]
    _debug.logic(
        "subprocess.argv_stripped",
        stripped=list(stripped),
        before=len(args),
        after=len(kept),
    )
    return kept


def dumpstacks(
    sig: int | None = None,
    frame: object = None,
    thread_idents: set[int] | None = None,
    log_level: int = logging.INFO,
) -> None:
    code = []

    def extract_stack(stack):
        for filename, lineno, name, line in traceback.extract_stack(stack):
            yield f'File: "{filename}", line {lineno}, in {name}'
            if line:
                yield f"  {line.strip()}"

    threads_info: dict[int | None, dict[str, Any]] = {
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
            elapsed = thread_info.get("query_time")
            perf_t0 = thread_info.get("perf_t0")
            remaining_time = None
            query_time = None
            if elapsed is not None and perf_t0:
                remaining_time = f"{real_time() - perf_t0 - elapsed:.3f}"
                query_time = f"{elapsed:.3f}"
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
            code.extend(extract_stack(stack))

    _logger.log(log_level, "\n".join(code))
    _debug.lifecycle(
        "subprocess.stacks_dumped",
        signal=sig,
        threads=len(threads_info),
        selected=None if not thread_idents else len(thread_idents),
        lines=len(code),
    )

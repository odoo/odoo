import logging
import optparse  # noqa: TID251  the argv is optparse's; stripping it must tokenize the same way
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


_STRIPPED_DESTS = frozenset(
    {"save", "init", "update", "reinit", "overwrite_existing_translations"}
)


def _consumed_values(option: optparse.Option, arg: str, rest: list[str]) -> int:
    if not option.takes_value():
        return 0
    if (
        arg in config.optional_options
        and "=" not in arg
        and (not rest or rest[0].startswith("-"))
    ):
        return 0
    return option.nargs or 1


def _strip_long(
    parser: optparse.OptionParser, arg: str, rest: list[str], dests: frozenset[str]
) -> tuple[list[str], int]:
    name, eq, _value = arg.partition("=")
    try:
        option = parser._long_opt[parser._match_long_opt(name)]
    except optparse.BadOptionError:
        return [arg], 0
    consumed = 0 if eq else _consumed_values(option, arg, rest)
    if option.dest in dests:
        return [], consumed
    return [arg, *rest[:consumed]], consumed


def _strip_short(
    parser: optparse.OptionParser, arg: str, rest: list[str], dests: frozenset[str]
) -> tuple[list[str], int]:
    kept = ""
    for pos, char in enumerate(arg[1:], start=2):
        option = parser._short_opt.get("-" + char)
        if option is None:
            return ["-" + kept + arg[pos - 1 :]], 0
        if not option.takes_value():
            if option.dest not in dests:
                kept += char
            continue
        attached = arg[pos:]
        consumed = 0 if attached else option.nargs or 1
        if option.dest in dests:
            return (["-" + kept] if kept else []), consumed
        return ["-" + kept + char + attached, *rest[:consumed]], consumed
    return (["-" + kept] if kept else []), 0


def stripped_sys_argv(*strip_args: str) -> list[str]:
    parser = config.parser
    unknown = [s for s in strip_args if not parser.has_option(s)]
    if unknown:
        msg = f"Unknown option(s) to strip: {', '.join(unknown)}"
        raise ValueError(msg)
    dests = _STRIPPED_DESTS | {parser.get_option(s).dest for s in strip_args}

    # the parser drops a retired option and its value before it reads the rest;
    # the argv read here must be the one the parser read
    args = sys.argv[:1] + config._without_retired_cli_options(sys.argv[1:])[0]
    kept = args[:1]
    i = 1
    while i < len(args):
        arg = args[i]
        rest = args[i + 1 :]
        if arg == "--":
            kept.extend(args[i:])
            break
        if arg.startswith("--"):
            tokens, consumed = _strip_long(parser, arg, rest, dests)
        elif arg.startswith("-") and arg != "-":
            tokens, consumed = _strip_short(parser, arg, rest, dests)
        else:
            tokens, consumed = [arg], 0
        kept.extend(tokens)
        i += 1 + consumed
    _debug.logic(
        "subprocess.argv_stripped",
        stripped=sorted(dests),
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

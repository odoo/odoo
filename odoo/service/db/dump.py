import base64
import functools
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import odoo.db
import odoo.release
import odoo.tools
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import exec_pg_environ, get_pg_tool_path

from .._env import get_env_float
from ._checks import check_db_management_enabled, check_db_name
from .listing import check_db_exposed

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from odoo.db import BaseCursor
else:
    BaseCursor = Any

_logger = logging.getLogger("odoo.service.db")
_debug = DebugLog(__name__)


BACKUP_FORMATS = frozenset({"zip", "dump"})


def _get_pg_dump_total_timeout() -> float:
    return get_env_float("ODOO_PG_DUMP_TOTAL_TIMEOUT", 3600.0, logger=_logger)


@check_db_management_enabled
def exp_dump(db_name: str, backup_format: str) -> str:
    check_db_exposed(db_name)
    CHUNK_SIZE = 3 * 1024 * 1024
    encoded = bytearray()
    with _debug.perf("database.dump.encoded", db=db_name, format=backup_format) as span:
        with tempfile.TemporaryFile(mode="w+b") as t:
            dump_db(db_name, t, backup_format)
            t.seek(0)
            while chunk := t.read(CHUNK_SIZE):
                encoded.extend(base64.b64encode(chunk))
        span.set(bytes=len(encoded))
    return encoded.decode("ascii")


def dump_db_manifest(cr: BaseCursor) -> dict[str, Any]:
    v = cr.connection.info.server_version
    pg_version = f"{v // 10000}.{v % 10000}"
    cr.execute(
        "SELECT name, db_version FROM ir_module_module WHERE state = 'installed'"
    )
    modules = dict(cr.fetchall())
    _debug.perf.count(
        "database.dump.manifest",
        db=getattr(cr, "dbname", None),
        modules=len(modules),
        pg_version=pg_version,
    )
    return {
        "odoo_dump": "1",
        "db_name": cr.dbname,
        "version": odoo.release.version,
        "version_info": odoo.release.version_info,
        "major_version": odoo.release.major_version,
        "pg_version": pg_version,
        "modules": modules,
    }


def _prepare_timeout_error(timeout: float) -> RuntimeError:
    return RuntimeError(
        f"pg_dump exceeded {timeout:.0f}s wall-clock timeout and was "
        f"terminated.  Set ODOO_PG_DUMP_TOTAL_TIMEOUT for slower DBs."
    )


def _prepare_pg_dump_failed_error(returncode: int, stderr: bytes) -> RuntimeError:
    return RuntimeError(
        f"pg_dump failed (exit {returncode}): {stderr.decode(errors='replace').strip()}"
    )


_STALL_SIGKILL_GRACE_S = 10.0


_STDERR_DRAIN_JOIN_S = 10.0


def _drain_pipe(pipe: IO[bytes], sink: list[bytes]) -> None:
    try:
        while chunk := pipe.read(4096):
            sink.append(chunk)
    except OSError, ValueError:
        pass


def _kill_pg_dump_on_stall(
    proc: subprocess.Popen, total_timeout: float, stall_killed: list[bool]
) -> None:
    stall_killed[0] = True
    _logger.error(
        "pg_dump exceeded total wall-clock timeout (%.0fs); sending SIGTERM",
        total_timeout,
    )
    _debug.logic(
        "database.dump.stalled", pid=getattr(proc, "pid", None), timeout=total_timeout
    )
    with suppress(ProcessLookupError):
        proc.terminate()
    try:
        proc.wait(timeout=_STALL_SIGKILL_GRACE_S)
    except subprocess.TimeoutExpired:
        _logger.error(
            "pg_dump ignored SIGTERM %.0fs after stall; sending SIGKILL",
            _STALL_SIGKILL_GRACE_S,
        )
        _debug.logic(
            "database.dump.sigkill", pid=getattr(proc, "pid", None), after="stall"
        )
        with suppress(ProcessLookupError):
            proc.kill()


def _reap_pg_dump(proc: subprocess.Popen) -> None:
    wait_timeout = get_env_float("ODOO_PG_DUMP_WAIT_TIMEOUT", 30.0, logger=_logger)
    try:
        proc.wait(timeout=wait_timeout)
    except subprocess.TimeoutExpired:
        _logger.error(
            "pg_dump did not exit within %.0fs after stdout EOF; sending SIGTERM",
            wait_timeout,
        )
        _debug.logic(
            "database.dump.reap_timed_out",
            pid=getattr(proc, "pid", None),
            timeout=wait_timeout,
        )
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _logger.error("pg_dump still alive; sending SIGKILL")
            _debug.logic(
                "database.dump.sigkill", pid=getattr(proc, "pid", None), after="reap"
            )
            proc.kill()
            proc.wait()


def _run_pg_dump(cmd: list[str], env: dict, stream: IO[bytes]) -> None:
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.stdout, proc.stderr
    assert stdout is not None and stderr is not None

    stderr_chunks: list[bytes] = []
    stderr_thread = threading.Thread(
        target=_drain_pipe,
        args=(stderr, stderr_chunks),
        name="odoo.service.db.pg_dump.stderr",
        daemon=True,
    )
    stderr_thread.start()

    total_timeout = _get_pg_dump_total_timeout()
    stall_killed = [False]
    stall_timer = threading.Timer(
        total_timeout,
        functools.partial(_kill_pg_dump_on_stall, proc, total_timeout, stall_killed),
    )
    stall_timer.daemon = True
    stall_timer.start()
    try:
        with _debug.perf(
            "database.dump.pg_dump",
            mode="streaming",
            pid=getattr(proc, "pid", None),
            timeout=total_timeout,
        ):
            shutil.copyfileobj(stdout, stream)
    finally:
        stall_timer.cancel()
        stdout.close()
        stderr_thread.join(timeout=_STDERR_DRAIN_JOIN_S)
        if stderr_thread.is_alive():
            _logger.warning(
                "pg_dump stderr drain still running after %.0fs; leaving the "
                "pipe to the interpreter",
                _STDERR_DRAIN_JOIN_S,
            )
            _debug.logic(
                "database.dump.stderr_drain_stuck",
                pid=getattr(proc, "pid", None),
                join_s=_STDERR_DRAIN_JOIN_S,
            )
        else:
            stderr.close()
        _reap_pg_dump(proc)
        _debug.lifecycle(
            "database.dump.reaped",
            pid=getattr(proc, "pid", None),
            returncode=proc.returncode,
            stall_killed=stall_killed[0],
            stderr_chunks=len(stderr_chunks),
        )
    if stall_killed[0] and proc.returncode != 0:
        raise _prepare_timeout_error(total_timeout)
    if proc.returncode != 0:
        raise _prepare_pg_dump_failed_error(proc.returncode, b"".join(stderr_chunks))


def _iter_filestore_files(root: str) -> Iterator[str]:
    root_real = os.path.realpath(root)
    stack = [root]
    while stack:
        with os.scandir(stack.pop()) as it:
            entries = sorted(it, key=lambda entry: entry.name)
        stack.extend(
            entry.path
            for entry in reversed(entries)
            if entry.is_dir(follow_symlinks=False)
        )
        for entry in entries:
            if entry.is_file(follow_symlinks=False):
                yield entry.path
            elif entry.is_symlink():
                real = os.path.realpath(entry.path)
                if not Path(real).is_file():
                    continue
                if os.path.commonpath([root_real, real]) != root_real:
                    _logger.warning(
                        "DUMP DB: skipping filestore entry %r, it resolves outside "
                        "the filestore (%r)",
                        entry.path,
                        real,
                    )
                    _debug.logic(
                        "database.dump.filestore_entry_skipped", path=entry.path
                    )
                    continue
                yield entry.path


def _add_filestore_to_zip(zipf: zipfile.ZipFile, filestore: str) -> None:
    if not Path(filestore).is_dir():
        _debug.logic("database.dump.filestore_absent", filestore=filestore)
        return
    with _debug.perf("database.dump.filestore_added", filestore=filestore) as span:
        files = 0  # debuglog
        for path in _iter_filestore_files(filestore):
            zipf.write(path, "filestore/" + os.path.relpath(path, filestore))
            files += 1  # debuglog
        span.set(files=files)


def _write_zip_dump(
    db_name: str,
    stream: IO[bytes],
    cmd: list[str],
    env: dict,
    with_filestore: bool,
) -> None:
    with zipfile.ZipFile(
        stream, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
    ) as zipf:
        db = odoo.db.db_connect(db_name)
        with db.cursor() as cr:
            with _debug.perf("database.dump.manifest_built", cr=cr, db=db_name):
                manifest = dump_db_manifest(cr)
        zipf.writestr("manifest.json", json.dumps(manifest, indent=4))
        _debug.pipeline("database.dump.zip.manifest_written", db=db_name)
        with zipf.open("dump.sql", "w", force_zip64=True) as sql_member:
            _run_pg_dump(cmd, env, sql_member)
        _debug.pipeline(
            "database.dump.zip.sql_written", db=db_name, filestore=with_filestore
        )
        if with_filestore:
            _add_filestore_to_zip(zipf, odoo.tools.config.filestore(db_name))


@check_db_management_enabled
def dump_db(
    db_name: str,
    stream: IO[bytes] | None,
    backup_format: str = "zip",
    with_filestore: bool = True,
) -> IO[bytes] | None:
    check_db_name(db_name)
    if backup_format not in BACKUP_FORMATS:
        _debug.logic("database.dump.invalid_format", db=db_name, format=backup_format)
        raise ValueError(
            f"Invalid backup format {backup_format!r}: expected one of "
            f"{', '.join(sorted(BACKUP_FORMATS))}."
        )

    _logger.info(
        "DUMP DB: %s format %s %s",
        db_name,
        backup_format,
        "with filestore" if with_filestore else "without filestore",
    )

    cmd = [get_pg_tool_path("pg_dump"), "--no-owner", db_name]
    env = exec_pg_environ()

    with _debug.perf(
        "database.dumped",
        db=db_name,
        format=backup_format,
        filestore=with_filestore,
        streaming=stream is not None,
    ):
        if backup_format == "zip":

            def write(target: IO[bytes]) -> None:
                _write_zip_dump(db_name, target, cmd, env, with_filestore)

        else:
            cmd.insert(-1, "--format=c")

            def write(target: IO[bytes]) -> None:
                _run_pg_dump(cmd, env, target)

        if stream is not None:
            write(stream)
            return None
        return _dump_into_tempfile(write)


def _dump_into_tempfile(write: Callable[[IO[bytes]], None]) -> IO[bytes]:
    t = tempfile.TemporaryFile()  # noqa: SIM115  the caller owns and closes it
    try:
        write(t)
        t.seek(0)
    except BaseException:
        t.close()
        raise
    return t

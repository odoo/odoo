import base64
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import IO, Literal

import odoo.api
import odoo.modules.neutralize
import odoo.modules.registry
import odoo.tools
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import exec_pg_environ, get_pg_tool_path

from .._env import get_env_float, get_env_int
from ._checks import check_db_management_enabled, check_db_name
from ._dump_scanner import _check_dump_sql_safe
from .lifecycle import (
    _announce_database,
    _check_filestore_dest_free,
    _create_empty_database,
    _rollback_new_database,
)
from .listing import exp_db_exist

_logger = logging.getLogger("odoo.service.db")
_debug = DebugLog(__name__)


_RESTORE_MAX_EXPANSION_RATIO = 50


_RESTORE_MIN_UNPACKED_BYTES = 100 * 1024 * 1024


_EXTRACT_CHUNK_BYTES = 1024 * 1024


def _extract_members_bounded(
    z: zipfile.ZipFile, members: list[str], dest: str, budget: int
) -> int:
    dest_path = Path(dest)
    written = 0
    with _debug.perf(
        "database.restore.extracted", members=len(members), budget=budget
    ) as span:
        for member in members:
            info = z.getinfo(member)
            target = dest_path / member
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open("wb") as out:
                while chunk := src.read(_EXTRACT_CHUNK_BYTES):
                    written += len(chunk)
                    if written > budget:
                        _debug.logic(
                            "database.restore.expansion_refused",
                            member=member,
                            written=written,
                            budget=budget,
                        )
                        raise RuntimeError(
                            f"Refusing to restore: the archive expands to more than "
                            f"{budget} bytes, over {_RESTORE_MAX_EXPANSION_RATIO}x its "
                            f"compressed size. Raise "
                            f"ODOO_RESTORE_MAX_EXPANSION_RATIO if this backup is "
                            f"genuinely that compressible."
                        )
                    out.write(chunk)
        span.set(written=written)
    return written


def _get_source_size(dump_file: str | os.PathLike | IO[bytes]) -> int:
    if isinstance(dump_file, (str, os.PathLike)):
        size = Path(dump_file).stat().st_size
        _debug.logic("database.restore.source_sized", source="path", bytes=size)
        return size
    pos = dump_file.tell()
    try:
        dump_file.seek(0, os.SEEK_END)
        size = dump_file.tell()
        _debug.logic("database.restore.source_sized", source="stream", bytes=size)
        return size
    finally:
        dump_file.seek(pos)


def _unpack_budget(dump_file: str | os.PathLike | IO[bytes]) -> int:
    ratio = get_env_int(
        "ODOO_RESTORE_MAX_EXPANSION_RATIO",
        _RESTORE_MAX_EXPANSION_RATIO,
        minimum=1,
        logger=_logger,
    )
    budget: int = max(_get_source_size(dump_file) * ratio, _RESTORE_MIN_UNPACKED_BYTES)
    _debug.logic("database.restore.budget", ratio=ratio, budget=budget)
    return budget


def _get_pg_restore_total_timeout() -> float:
    return get_env_float("ODOO_PG_RESTORE_TOTAL_TIMEOUT", 3600.0, logger=_logger)


@check_db_management_enabled
def exp_restore(db_name: str, data: str, copy: bool = False) -> Literal[True]:
    _STRIP_WS = str.maketrans("", "", " \t\n\r\v\f")
    CHUNK = 8192

    data_file = tempfile.NamedTemporaryFile(delete=False)  # noqa: SIM115  delete=False: the path outlives this scope
    try:
        with _debug.perf(
            "database.restore.decoded", db=db_name, chars=len(data)
        ) as span:
            accum = ""
            for i in range(0, len(data), CHUNK):
                accum += data[i : i + CHUNK].translate(_STRIP_WS)
                n_complete = (len(accum) // 4) * 4
                if n_complete:
                    data_file.write(base64.b64decode(accum[:n_complete]))
                    accum = accum[n_complete:]
            if accum:
                data_file.write(base64.b64decode(accum))
            span.set(bytes=data_file.tell())
        data_file.close()
        restore_db(db_name, data_file.name, copy=copy)
    finally:
        data_file.close()
        Path(data_file.name).unlink(missing_ok=True)
    return True


def _extract_zip_dump(
    dump_file: str | os.PathLike | IO[bytes], dump_dir: str
) -> str | None:
    with zipfile.ZipFile(dump_file, "r") as z:
        dump_dir_resolved = Path(dump_dir).resolve()
        for member in z.namelist():
            target = (dump_dir_resolved / member).resolve()
            if not target.is_relative_to(dump_dir_resolved):
                _debug.logic("database.restore.member_escapes", member=member)
                raise RuntimeError(
                    f"Refusing to restore: archive member {member!r} "
                    f"escapes the extraction directory"
                )

        if "dump.sql" not in z.namelist():
            _debug.logic("database.restore.no_dump_sql", members=len(z.namelist()))
            raise RuntimeError(
                "Refusing to restore: the archive contains no "
                "'dump.sql' member, so it is not an Odoo database "
                "backup."
            )

        filestore = [m for m in z.namelist() if m.startswith("filestore/")]
        _debug.pipeline(
            "database.restore.archive_listed",
            members=len(z.namelist()),
            filestore=len(filestore),
        )
        _extract_members_bounded(
            z,
            ["dump.sql"] + filestore,
            dump_dir,
            _unpack_budget(dump_file),
        )

    return str(Path(dump_dir, "filestore")) if filestore else None


def _get_restore_command(
    dump_file: str | os.PathLike | IO[bytes], dump_dir: str
) -> tuple[str, list[str], str | None]:
    if zipfile.is_zipfile(dump_file):
        filestore_path = _extract_zip_dump(dump_file, dump_dir)
        dump_sql_path = str(Path(dump_dir, "dump.sql"))
        _check_dump_sql_safe(dump_sql_path)
        pg_args = ["-X", "-q", "-v", "ON_ERROR_STOP=1", "-f", dump_sql_path]
        _debug.logic(
            "database.restore.command",
            tool="psql",
            filestore=filestore_path is not None,
        )
        return "psql", pg_args, filestore_path

    if not isinstance(dump_file, (str, os.PathLike)):
        _debug.logic("database.restore.refused", reason="raw_stream")
        raise TypeError(
            "a raw (non-zip) restore needs a file path, not an open file object"
        )
    _debug.logic("database.restore.command", tool="pg_restore", filestore=False)
    return (
        "pg_restore",
        ["--no-owner", "--exit-on-error", os.fspath(dump_file)],
        None,
    )


def _run_pg_restore(db: str, pg_cmd: str, pg_args: list[str]) -> None:
    timeout = _get_pg_restore_total_timeout()
    try:
        with _debug.perf(
            "database.restore.pg_restore", db=db, tool=pg_cmd, timeout=timeout
        ):
            r = subprocess.run(
                [get_pg_tool_path(pg_cmd), "--dbname=" + db, *pg_args],
                env=exec_pg_environ(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired as e:
        _debug.logic("database.restore.timed_out", db=db, tool=pg_cmd, timeout=timeout)
        raise RuntimeError(
            f"Restore of {db!r} exceeded {timeout:.0f}s wall-clock "
            f"timeout and was terminated.  Set "
            f"ODOO_PG_RESTORE_TOTAL_TIMEOUT for slower restores."
        ) from e
    if r.returncode != 0:
        _logger.error("RESTORE DB %r failed:\n%s", db, r.stderr)
        _debug.logic(
            "database.restore.tool_failed", db=db, tool=pg_cmd, returncode=r.returncode
        )
        raise RuntimeError(f"Couldn't restore database {db!r}:\n{r.stderr.strip()}")


def _finalize_restored_db(
    db: str, copy: bool, neutralize_database: bool, filestore_path: str | None
) -> None:
    with _debug.perf("database.restore.registry_loaded", db=db):
        registry = odoo.modules.registry.Registry.new(db, run_tests=False)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})
        if copy:
            env["ir.config_parameter"].init(force=True)
        if neutralize_database:
            odoo.modules.neutralize.neutralize_database(cr)
        _debug.pipeline(
            "database.restore.finalized",
            db=db,
            copy=copy,
            neutralized=neutralize_database,
            filestore=filestore_path is not None,
        )

        if filestore_path:
            filestore_dest = env["ir.attachment"]._get_filestore()
            if Path(filestore_dest).exists():
                _debug.logic(
                    "database.restore.filestore_race", db=db, dest=filestore_dest
                )
                raise RuntimeError(
                    f"Filestore {filestore_dest!r} appeared between "
                    f"pre-flight and move (race)."
                )
            with _debug.perf("database.restore.filestore_moved", db=db):
                shutil.move(filestore_path, filestore_dest)


@check_db_management_enabled
def restore_db(
    db: str,
    dump_file: str | os.PathLike | IO[bytes],
    copy: bool = False,
    neutralize_database: bool = False,
) -> None:
    if not isinstance(db, str):
        raise TypeError(f"db must be a str, got {type(db).__name__!r}")
    check_db_name(db)
    if exp_db_exist(db):
        _logger.warning("RESTORE DB: %s already exists", db)
        _debug.logic("database.restore.refused", db=db, reason="exists")
        raise RuntimeError(f"Database {db!r} already exists")

    fs_dest = odoo.tools.config.filestore(db)
    _check_filestore_dest_free(fs_dest, f"Cannot restore to {db!r}")

    _logger.info("RESTORING DB: %s", db)
    _create_empty_database(
        db, template="template0", force_unaccent=True, setup_if_exists=False
    )

    try:
        with tempfile.TemporaryDirectory() as dump_dir:
            pg_cmd, pg_args, filestore_path = _get_restore_command(dump_file, dump_dir)
            _run_pg_restore(db, pg_cmd, pg_args)
            _finalize_restored_db(db, copy, neutralize_database, filestore_path)

        _logger.info("RESTORE DB: %s", db)
        _debug.lifecycle(
            "database.restored",
            db=db,
            copy=copy,
            neutralized=neutralize_database,
            filestore=filestore_path is not None,
        )
    except Exception:
        _debug.logic("database.restore.failed", db=db)
        _rollback_new_database(db, "RESTORE DB")
        raise
    _announce_database(db)
